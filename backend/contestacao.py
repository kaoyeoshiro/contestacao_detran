# ... outros imports no topo
from flask import (
    Flask,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    make_response,
    g,
)
from flask_session import Session
from flask_cors import CORS
# ... resto dos seus imports

import os
import fitz  # PyMuPDF
import google.generativeai as genai
from werkzeug.utils import secure_filename
# import tempfile # Não será mais necessário para o texto_pdfs_original na sessão
import logging
from datetime import datetime
import re
import html
from markupsafe import escape
import uuid

# --- Configuração de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuração Inicial ---
app = Flask(__name__)
CORS(app)  # Habilita CORS para todas as rotas em desenvolvimento
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(32)) # Importante para assinar o cookie de ID

# --- Configuração do Flask-Session (Sessões no Lado do Servidor) ---
app.config['SESSION_TYPE'] = 'filesystem'  # Armazena sessões no sistema de arquivos
app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(__file__), '.flask_session') # Pasta para arquivos de sessão
app.config['SESSION_PERMANENT'] = False # Sessões expiram quando o navegador fecha (ou configure lifetime)
app.config['SESSION_USE_SIGNER'] = True # Assina o cookie de ID da sessão para segurança
# app.config['SESSION_FILE_THRESHOLD'] = 500 # Número de arquivos de sessão antes de começar a limpar (opcional)
Session(app) # Inicializa a extensão Flask-Session
# Garante que o diretório de sessão exista
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
logger.info(f"Flask-Session configurado para usar o sistema de arquivos em: {app.config['SESSION_FILE_DIR']}")


# --- Configuração do Modelo Gemini ---
model = None
TARGET_MODEL_NAME_BASE = 'gemini-2.5-flash-preview-05-20' 
ACTUAL_MODEL_NAME_LOADED = "NENHUM MODELO CARREGADO"

try:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    api_key_source = "variável de ambiente"
    if not GEMINI_API_KEY:
        # Descomente e substitua pela sua chave APENAS para teste local rápido.
        # Lembre-se dos riscos e NÃO FAÇA COMMIT desta linha com sua chave real.
        # GEMINI_API_KEY = "SUA_CHAVE_API_REAL_AQUI_PARA_TESTE_LOCAL" 
        # api_key_source = "hardcoded para teste"
        # if GEMINI_API_KEY == "SUA_CHAVE_API_REAL_AQUI_PARA_TESTE_LOCAL" or not GEMINI_API_KEY:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi definida.")

    logger.info(f"GEMINI_API_KEY obtida via {api_key_source}. Configurando genai...")
    genai.configure(api_key=GEMINI_API_KEY)

    model_names_to_try = [TARGET_MODEL_NAME_BASE, f'models/{TARGET_MODEL_NAME_BASE}']
    for model_name_attempt in model_names_to_try:
        try:
            logger.info(f"Tentando carregar modelo Gemini: '{model_name_attempt}'")
            model = genai.GenerativeModel(model_name_attempt)
            ACTUAL_MODEL_NAME_LOADED = model_name_attempt
            logger.info(f"Modelo Gemini '{ACTUAL_MODEL_NAME_LOADED}' carregado.")
            break 
        except Exception as e:
            logger.warning(f"Falha ao carregar modelo '{model_name_attempt}': {e}")
            if model_name_attempt == model_names_to_try[-1]:
                logger.error("Todas as tentativas de carregar o modelo Gemini falharam.", exc_info=True)
                raise ValueError(f"Não foi possível carregar um modelo Gemini. Último erro: {e}")
    if not model: raise EnvironmentError("Modelo Gemini não inicializado.")
except Exception as e: 
    logger.error(f"Erro Crítico na Configuração Inicial do Gemini: {e}", exc_info=True)

if model: logger.info(f"Configuração final: Modelo Gemini '{ACTUAL_MODEL_NAME_LOADED}' está carregado.")
else: logger.critical("Configuração final: Modelo Gemini NÃO CARREGADO. Geração de minuta INDISPONÍVEL.")

# --- Constantes ---
MAX_FILES = 5
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {'pdf'}
# COOKIE_SAFE_LIMIT_BYTES não é mais necessário para os dados principais da sessão

# --- Classes (MinutaGenerator, PDFProcessor, MinutaParser, HTMLGenerator) ---
# (As classes permanecem as mesmas da versão anterior, pois a lógica interna delas não muda
#  com a forma como a sessão é armazenada pelo Flask-Session)

class MinutaGenerator: # Mantida como antes
    def __init__(self, model_instance):
        self.model_instance = model_instance
    
    def generate_minuta(self, text_from_pdfs, instructions=""):
        if not self.model_instance:
            logger.error("MinutaGenerator: Modelo Gemini não está disponível/configurado.")
            return "Erro: O serviço de IA não está disponível no momento. Tente novamente mais tarde."

        prompt_template = self._build_prompt(text_from_pdfs, instructions)
        logger.info(f"MinutaGenerator: Prompt construído com {len(prompt_template)} caracteres.")
        
        try:
            logger.info("MinutaGenerator: Iniciando chamada para self.model_instance.generate_content")
            generation_config = genai.types.GenerationConfig(
                temperature=0.7, top_p=0.8, top_k=40, max_output_tokens=60000
            )
            response = self.model_instance.generate_content(
                contents=[prompt_template], 
                generation_config=generation_config,
            )
            logger.info("MinutaGenerator: Resposta recebida do modelo Gemini.")
            return self._extract_response_text(response)
        except Exception as e:
            error_detail = str(e)
            if "API_KEY_INVALID" in error_detail or "PermissionDenied" in error_detail or "PERMISSION_DENIED" in error_detail:
                 logger.error(f"MinutaGenerator: Erro de API Key ou Permissão: {error_detail}", exc_info=True)
                 return "Erro: Falha na autenticação com o serviço de IA. Verifique a API Key e permissões."
            elif "Billing" in error_detail or "billing" in error_detail:
                 logger.error(f"MinutaGenerator: Problema de faturamento: {error_detail}", exc_info=True)
                 return "Erro: Problema com a conta de faturamento da API Key."
            else:
                 logger.error(f"MinutaGenerator: Erro ao chamar Gemini: {error_detail}", exc_info=True)
                 return f"Erro inesperado ao contatar o serviço de IA: {error_detail}"

    def _build_prompt(self, text_from_pdfs, instructions=""):
        # (Seu prompt extenso e detalhado permanece aqui, como antes)
        base_prompt = f"""
# PROMPT PARA CONTESTAÇÃO JURÍDICA PROFUNDA E ANALÍTICA - TRANSFERÊNCIA DE PONTOS NA CNH

Você é um procurador do Estado especializado em ações de trânsito com vasta experiência em defesa de atos administrativos. Abaixo estão os conteúdos de uma petição inicial e documentos auxiliares em uma ação judicial de **TRANSFERÊNCIA DE PONTOS NA CNH**.

**CONTEXTO ESPECÍFICO:** A ação envolve pedido de transferência judicial de pontos após perda do prazo administrativo (art. 257, § 7º do CTB), baseada apenas em declaração singela do suposto condutor, sem provas robustas que desconstituam a presunção legal de responsabilidade do proprietário do veículo.

Com base nessas informações, redija uma **MINUTA DE CONTESTAÇÃO COMPLETA E DETALHADA** que tenha **OBRIGATORIAMENTE ENTRE 5 A 10 PÁGINAS**, estruturando o texto nos seguintes blocos:

## 1. **RELATÓRIO DOS FATOS** (1-2 páginas)
Descreva de forma **minuciosa e analítica** o conteúdo da petição inicial, incluindo:
- Narrativa cronológica detalhada dos eventos
- Análise crítica das alegações do autor
- Contextualização dos fatos no âmbito administrativo
- Identificação de inconsistências ou omissões na inicial
- Descrição pormenorizada dos documentos juntados
- Linguagem impessoal, técnica e objetiva

## 2. **FUNDAMENTAÇÃO JURÍDICA** (3-6 páginas)
Apresente argumentação **extensa e aprofundada** com os seguintes subtópicos obrigatórios:

### 2.1. **DO MÉRITO - ASPECTOS MATERIAIS**
- **Análise do Código de Trânsito Brasileiro (Lei 9.503/97)**
  - Art. 257, § 7º - prazo para indicação do condutor
  - Consequências da perda do prazo administrativo
  - Sistema de pontuação e penalidades
  - Competência administrativa para autuação e aplicação de sanções
- **Princípios do Direito Administrativo aplicáveis**
  - Legalidade estrita
  - Presunção de legitimidade dos atos administrativos
  - Auto-executoriedade
  - Imperatividade
- **Normas administrativas pertinentes**
  - Resoluções do CONTRAN sobre notificação e defesa
  - Sistema de Notificação Eletrônica (SNE)
  - Procedimentos para suspensão do direito de dirigir
  - Instruções normativas sobre identificação de condutores

### 2.3. **JURISPRUDÊNCIA CONSOLIDADA**
- Precedentes do STJ sobre transferência de pontos
- Decisões dos Tribunais de Justiça estaduais
- Orientações dos Tribunais Regionais Federais
- Súmulas aplicáveis ao caso

### 2.4. **INSUFICIÊNCIA PROBATÓRIA DA MERA DECLARAÇÃO**
- **Inadequação da prova apresentada pelo autor**
  - Análise crítica da declaração singela e simplória
  - Ausência de elementos corroborativos
  - Inexistência de justificativa para inércia administrativa
- **Necessidade de prova irrefutável e absolutamente idônea**
  - Padrão probatório exigido para desconstituir presunção legal
  - Elementos que poderiam demonstrar a alegada inocência
  - Comparação com casos de transferência deferida judicialmente
- **Risco de fraudes e impunidade**
  - Proteção do sistema contra declarações oportunistas
  - Preservação da efetividade das normas de trânsito
  - Impedimento de ganho econômico indevido
- Refutação ponto a ponto das alegações do autor
- Demonstração da correção do procedimento administrativo
- Evidenciação da observância do devido processo legal
- Comprovação da regularidade da notificação

### 2.5. **QUESTÕES PROBATÓRIAS**
- Análise da prova documental
- Discussão sobre inversão do ônus da prova
- Necessidade de perícia técnica (se aplicável)
- Valoração das provas administrativas

## 3. **PEDIDOS** (1 página)
Elabore pedidos **abrangentes e fundamentados**:
- Pedidos preliminares (se aplicáveis)
- Pedido principal de improcedência
- Pedidos subsidiários
- Condenação em honorários e custas
- Outros pedidos pertinentes

## DIRETRIZES OBRIGATÓRIAS PARA EXTENSÃO E QUALIDADE:

### **EXTENSÃO MÍNIMA EXIGIDA:**
- **MÍNIMO ABSOLUTO: 5 páginas completas**
- **IDEAL: 7-10 páginas**
- Cada página deve conter aproximadamente 30-35 linhas
- Parágrafos bem desenvolvidos com 4-8 linhas cada

### **CARACTERÍSTICAS DA ARGUMENTAÇÃO:**
- **PROFUNDIDADE ANALÍTICA**: Cada argumento deve ser desenvolvido em múltiplos parágrafos
- **CITAÇÕES EXTENSAS**: Inclua trechos relevantes da legislação e jurisprudência
- **ANÁLISE COMPARATIVA**: Compare casos similares e suas soluções
- **ABORDAGEM MULTIDISCIPLINAR**: Considere aspectos administrativos, constitucionais e processuais
- **ARGUMENTAÇÃO SUBSIDIÁRIA**: Desenvolva argumentos alternativos e complementares

### **ESTRUTURA TEXTUAL OBRIGATÓRIA:**
- **Parágrafos longos e bem fundamentados** (mínimo 4 linhas cada)
- **Subdivisões detalhadas** com desenvolvimento completo de cada tópico
- **Transições argumentativas** entre os diferentes pontos
- **Conclusões parciais** ao final de cada seção principal
- **Linguagem jurídica rebuscada** mas clara e precisa

### **ELEMENTOS DE ENRIQUECIMENTO DO TEXTO:**
- Histórico legislativo das normas aplicáveis
- Evolução jurisprudencial sobre o tema
- Análise doutrinária de renomados juristas
- Comparação com legislações de outros países (quando pertinente)
- Impactos sociais e econômicos da questão

### **FORMATAÇÃO E APRESENTAÇÃO:**
- Títulos e subtítulos claramente hierarquizados
- Numeração sequencial dos argumentos principais
- Citações em formatação adequada
- Referencias bibliográficas completas
- Linguagem jurídica formal, técnica e erudita

### **CONTROLE DE QUALIDADE:**
- Evite repetições desnecessárias MAS desenvolva cada argumento completamente
- Mantenha coerência lógica entre os argumentos
- Certifique-se de que cada seção atinja o tamanho mínimo especificado
- Verifique se a contestação como um todo possui densidade argumentativa suficiente

**ATENÇÃO ESPECIAL:** A contestação deve demonstrar conhecimento jurídico profundo e análise minuciosa do caso, com desenvolvimento completo de todos os aspectos processuais e materiais envolvidos. Cada argumento deve ser tratado de forma exaustiva, com fundamentação múltipla e abordagem de diversos ângulos da questão jurídica.

Conteúdo dos documentos:
\"\"\"
{text_from_pdfs}
\"\"\"
"""
        if instructions:
            base_prompt += f"""

INSTRUÇÕES ESPECÍFICAS PARA AJUSTE:
\"\"\"
{instructions}
\"\"\"

Incorpore estas instruções na reformulação da minuta, mantendo a estrutura e qualidade jurídica.
"""
        return base_prompt
    
    def _extract_response_text(self, response): # Mantida como antes
        try:
            if response is None: logger.warning("MinutaGenerator: Resposta Gemini é None."); return "Erro: Nenhuma resposta IA."
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback and hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                reason = response.prompt_feedback.block_reason.name 
                logger.error(f"MinutaGenerator: Geração bloqueada. Razão: {reason}"); return f"Erro: Solicitação bloqueada ({reason})."
            if not hasattr(response, 'candidates') or not response.candidates: logger.warning("MinutaGenerator: Resposta sem 'candidates'."); return "Erro: Resposta inválida (sem candidatos)."
            first_candidate = response.candidates[0]
            finish_reason_map = {0:"UNSPECIFIED",1:"STOP",2:"MAX_TOKENS",3:"SAFETY",4:"RECITATION",5:"OTHER"}
            finish_reason_value = first_candidate.finish_reason.value if hasattr(first_candidate.finish_reason, 'value') else first_candidate.finish_reason
            if finish_reason_value != 1:
                 reason_str = finish_reason_map.get(finish_reason_value, str(finish_reason_value))
                 logger.error(f"MinutaGenerator: Geração não finalizada: {reason_str} ({finish_reason_value})")
                 if finish_reason_value == 3: 
                     safety_details = "; ".join([f"{r.category.name}:{r.probability.name}" for r in first_candidate.safety_ratings]) if hasattr(first_candidate,'safety_ratings') else "N/A"
                     return f"Erro: Geração interrompida por segurança ({reason_str}). Detalhes: {safety_details}."
                 return f"Erro: Geração não concluída (Razão: {reason_str})."
            if first_candidate.content and first_candidate.content.parts:
                all_text_parts = [part.text for part in first_candidate.content.parts if hasattr(part, 'text')]
                if all_text_parts: return "".join(all_text_parts)
            if hasattr(response, 'text') and response.text: return response.text
            logger.warning(f"MinutaGenerator: Resposta Gemini inesperada: {str(response)[:200]}..."); return "Erro: Resposta Gemini inesperada/vazia."
        except Exception as e: logger.error(f"MinutaGenerator: Erro extrair texto: {e}", exc_info=True); return f"Erro interno ao processar resposta IA."

class PDFProcessor: # Mantida
    @staticmethod
    def allowed_file(filename): return ('.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS)
    @staticmethod
    def extract_text_from_pdfs(pdf_files):
        full_text, filenames, errors = "", [], []
        for pdf_file in pdf_files:
            if not pdf_file or not pdf_file.filename: errors.append("Arquivo inválido."); continue
            s_filename = secure_filename(pdf_file.filename)
            if not PDFProcessor.allowed_file(s_filename): errors.append(f"'{s_filename}' não é PDF."); continue
            try:
                pdf_file.seek(0, os.SEEK_END); file_size = pdf_file.tell(); pdf_file.seek(0, os.SEEK_SET)
                if file_size > MAX_FILE_SIZE: errors.append(f"{s_filename} ({(file_size/(1024*1024)):.1f}MB) > limite."); continue
                pdf_content = pdf_file.read()
                if not pdf_content: errors.append(f"{s_filename} vazio."); continue
                doc = fitz.open(stream=pdf_content, filetype="pdf")
                file_text = "".join([f"--- Pág {i+1} ---\n{p.get_text('text')}\n\n" for i,p in enumerate(doc) if p.get_text("text").strip()])
                if file_text.strip(): full_text += f"=== ARQUIVO: {s_filename} ===\n{file_text}\n"; filenames.append(s_filename)
                else: errors.append(f"{s_filename} sem texto legível.")
                doc.close()
            except Exception as e: errors.append(f"Erro em {s_filename}: {e}"); logger.error(f"PDFProcessor: Erro {s_filename}: {e}", exc_info=True)
        return full_text, filenames, errors

class MinutaParser: # Mantida
    @staticmethod
    def parse_minuta_to_single_block(minuta_text):
        if not minuta_text or (isinstance(minuta_text, str) and minuta_text.startswith("Erro:")):
            return {"CONTESTAÇÃO COMPLETA": minuta_text if minuta_text else "Nenhuma minuta ou erro."}
        return {"CONTESTAÇÃO COMPLETA": minuta_text}

class HTMLGenerator: # Mantida
    @staticmethod
    def _escape_html_attribute(value):
        if not value: return ""
        return html.escape(str(value), quote=True) 
    @staticmethod
    def format_text_for_html(text_content):
        if not text_content:
            return ""

        # Normaliza quebras de linha universais para \n primeiro
        processed_text = text_content.replace('\r\n', '\n').replace('\r', '\n')
        
        lines = processed_text.split('\n')
        processed_lines = []

        for line in lines:
            # 1. Escapa a linha individualmente para neutralizar qualquer HTML
            #    que a IA possa ter gerado naquela linha.
            line_escaped = escape(line) # Usa escape de markupsafe

            # 2. Converte **texto** para <strong>texto</strong> na linha já escapada.
            #    Os asteriscos não são alterados por escape(), então re.sub os encontrará.
            #    O conteúdo DENTRO dos ** (grupo \1) já foi escapado se continha HTML.
            line_with_strong = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line_escaped)
            
            processed_lines.append(line_with_strong)
        
        # Junta as linhas processadas com <br>\n
        return "<br>\n".join(processed_lines)
    @staticmethod
    def generate_page(minuta_data=None, erro_msg="", sucesso_msg="", filenames_processados=None, warnings=None): # Removido temp_text_file_id
        warnings = warnings or []; filenames_processados = filenames_processados or []
        html_output_content = f"""
<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gerador de Minutas de Contestação - PGE</title><style>{HTMLGenerator._get_css()}</style></head><body><div class="container">
<header><h1>📋 Gerador de Minutas de Contestação</h1><p class="subtitle">PGE-MS - Automação Jurídica com IA</p></header>
{HTMLGenerator._generate_messages(erro_msg, sucesso_msg, warnings)}
{HTMLGenerator._generate_upload_form()}
{HTMLGenerator._generate_processed_files(filenames_processados)}
{HTMLGenerator._generate_minuta_display(minuta_data)} 
<footer><p>LAB-PGE • Inovação e Tecnologia • {datetime.now().strftime('%Y')} Versão: FlaskSession</p></footer>
</div><script>{HTMLGenerator._get_javascript()}</script></body></html>"""
        return make_response(html_output_content)
    @staticmethod
    def _get_css(): return """* { margin: 0; padding: 0; box-sizing: border-box; } /* ... seu CSS ... */ body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; } .container { max-width: 1200px; margin: 20px auto; padding: 20px; background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); } header { text-align: center; margin-bottom: 30px; border-bottom: 3px solid #667eea; padding-bottom: 20px; } header h1 { color: #2c3e50; font-size: 2.5em; margin-bottom: 10px; } .subtitle { color: #7f8c8d; font-size: 1.1em; } .section { margin: 30px 0; padding: 25px; border-radius: 10px; } .upload-section { background: #f8f9fa; border-left: 5px solid #28a745; } .minuta-content-display { white-space: pre-wrap; font-family: 'Courier New', monospace; padding: 20px; border: 2px solid #dee2e6; border-radius: 8px; background-color: #f8f9fa; min-height: 250px; max-height: 600px; overflow-y: auto; line-height: 1.5; text-align: justify; } .minuta-content-display strong { font-weight: bold; }  .minuta-section { background: #e9ecef; border-left: 5px solid #007bff; }  .adjust-section { background: #fff3cd; border-left: 5px solid #ffc107; }  h2 { color: #2c3e50; margin-bottom: 20px; font-size: 1.8em; } h3 { color: #495057; margin-bottom: 15px; font-size: 1.3em; } label { display: block; margin: 15px 0 8px 0; font-weight: 600; color: #495057; } input[type="file"], textarea { width: 100%; padding: 12px; border: 2px solid #dee2e6; border-radius: 8px; font-size: 14px; transition: border-color 0.3s ease; margin-bottom: 10px; } input[type="file"]:focus, textarea:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); } .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 25px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: 600; transition: transform 0.2s ease, box-shadow 0.2s ease; } .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); } .btn:active { transform: translateY(0); } .alert { padding: 15px; margin: 20px 0; border-radius: 8px; font-weight: 500; word-wrap: break-word; } .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; } .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; } .alert-warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; } .file-list { list-style: none; padding: 0; } .file-item { background: #e9ecef; padding: 10px 15px; margin: 8px 0; border-radius: 6px; border-left: 4px solid #28a745; display: flex; align-items: center; } .file-item::before { content: '📄'; margin-right: 10px; font-size: 1.2em; } .minuta-block { margin: 25px 0; border: none; border-radius: 10px; overflow: hidden; box-shadow: none; } .minuta-block h3 { background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; padding: 15px 20px; margin: 0; font-size: 1.4em; border-top-left-radius: 8px; border-top-right-radius: 8px;} footer { text-align: center; margin-top: 50px; padding-top: 20px; border-top: 2px solid #dee2e6; color: #6c757d; } .loading { display: none; text-align: center; margin: 20px 0; } .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto; } @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } } @media (max-width: 768px) { .container { margin: 10px; padding: 15px; border-radius: 10px; } header h1 { font-size: 2em; } .section { padding: 20px; } }"""
    @staticmethod
    def _get_javascript(): return """ function showLoading(formElement) { /* ... seu JS ... */ const submitBtn = formElement.querySelector('input[type="submit"]'); const loadingDiv = document.querySelector('.loading'); if (submitBtn) { submitBtn.disabled = true; submitBtn.value = 'Processando...';} if (loadingDiv) { loadingDiv.style.display = 'block';}} function validateFileUpload(input) { /* ... seu JS ... */ const files = input.files; const maxSize = 10485760; const maxFiles = 5; if (files.length === 0 && input.required) { alert('Selecione ao menos um PDF.'); return false;} if (files.length > maxFiles) { alert(`Máximo ${maxFiles} arquivos.`); input.value = ''; return false;} for (let file of files) { if (file.size > maxSize) { alert(`${file.name} (${(file.size/1048576).toFixed(1)}MB) > limite de ${(maxSize/1048576).toFixed(0)}MB`); input.value = ''; return false;} if (!file.name.toLowerCase().endsWith('.pdf')) { alert(`${file.name} não é PDF.`); input.value = ''; return false;}} return true;} function copyToClipboard(elementId) { /* ... seu JS ... */ const el = document.getElementById(elementId); if (!el) return; let text = el.innerText || el.textContent; if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(text).then(() => alert('Copiado!'), () => alert('Falha ao copiar.'));} else { try { const r = document.createRange(); r.selectNodeContents(el); window.getSelection().removeAllRanges(); window.getSelection().addRange(r); document.execCommand('copy'); alert('Copiado (fallback)!'); window.getSelection().removeAllRanges(); } catch(e){alert('Falha ao copiar (fallback).');}}} document.addEventListener('DOMContentLoaded', () => { document.querySelectorAll('form').forEach(f => f.addEventListener('submit', function(e){ if(this.elements.action && this.elements.action.value === 'upload_pdfs'){ const fi=this.querySelector('input[type="file"][name="pdfs"]'); if(fi && !validateFileUpload(fi)){e.preventDefault(); const sb=this.querySelector('input[type="submit"]'); if(sb){sb.disabled=false; sb.value='🚀 Gerar Minuta';} const ld=document.querySelector('.loading'); if(ld)ld.style.display='none'; return;}} showLoading(this);})); const fiu=document.querySelector('input[type="file"][name="pdfs"]'); if(fiu)fiu.addEventListener('change', function(){validateFileUpload(this);});});"""
    @staticmethod
    def _generate_messages(e, s, w):
        html_messages = [] # Usar uma lista para juntar no final é mais eficiente
        if e: # Erro
            html_messages.append(f'<div class="alert alert-error">❌ {escape(e)}</div>')
        if s: # Sucesso
            html_messages.append(f'<div class="alert alert-success">✅ {escape(s)}</div>')
        if w: # Warnings (lista de avisos)
            for warning_message in w:
                html_messages.append(f'<div class="alert alert-warning">⚠️ {escape(warning_message)}</div>')
        return "".join(html_messages)
    @staticmethod
    def _generate_upload_form(): return """<div class="section upload-section"><h2>1. Upload de Documentos</h2><form method="POST" enctype="multipart/form-data" action="/"><input type="hidden" name="action" value="upload_pdfs"><label for="pdfs">📁 Selecione de 1 a 5 arquivos PDF (máximo 10MB cada):</label><input type="file" name="pdfs" multiple accept=".pdf" required><p style="color:#6c757d;font-size:0.9em;margin-top:5px;">Tipos aceitos: PDF • Max por arquivo: 10MB</p><input type="submit" value="🚀 Gerar Minuta" class="btn" style="margin-top:20px;"></form><div class="loading" style="margin-top:15px;"><div class="spinner"></div><p>Processando e gerando...</p></div></div>"""
    @staticmethod
    def _generate_processed_files(f_names):
        if not f_names: return ""
        li = "".join([f'<li class="file-item">{escape(fn)}</li>' for fn in f_names])
        return f'<div class="section"><h3 style="color:#495057;">📎 Arquivos Processados:</h3><ul class="file-list">{li}</ul></div>'
    
    @staticmethod
    def _generate_minuta_display(minuta_data): # Removido temp_text_file_id como argumento explícito
        if not minuta_data or not minuta_data.get("CONTESTAÇÃO COMPLETA") or \
           (isinstance(minuta_data["CONTESTAÇÃO COMPLETA"], str) and 
            (minuta_data["CONTESTAÇÃO COMPLETA"].startswith("Erro:") or 
             minuta_data["CONTESTAÇÃO COMPLETA"] == "Nenhuma minuta para exibir." or
             minuta_data["CONTESTAÇÃO COMPLETA"] == "Nenhuma minuta ou erro." or
             minuta_data["CONTESTAÇÃO COMPLETA"] == "Nenhuma minuta para exibir ou ocorreu um erro.")):
            return ""
            
        minuta_completa_texto = minuta_data["CONTESTAÇÃO COMPLETA"]
        minuta_formatada_html = HTMLGenerator.format_text_for_html(minuta_completa_texto)
        
        # O texto original para ajuste agora virá da sessão, gerenciado pelo Flask-Session
        # Não precisamos mais passar o ID do arquivo temporário para o template aqui.
        # O _handle_ajustar_minuta lerá 'texto_pdfs_original' da sessão.

        html_display = '<div class="section minuta-section"><h2>2. ⚖️ Minuta da Contestação Gerada</h2>'
        html_display += f"""
        <div class="minuta-block"><h3 style="border-bottom: 1px solid #004085;">CONTESTAÇÃO COMPLETA</h3>
        <div id="minuta-content" class="minuta-content-display">
        {minuta_formatada_html if minuta_formatada_html else '<p>Conteúdo da minuta não disponível.</p>'}</div>
        <button onclick="copyToClipboard('minuta-content')" class="btn" style="margin-top:15px; background: linear-gradient(135deg, #28a745 0%, #218838 100%);">Copiar Minuta</button>
        </div></div>"""
        
        # Só mostra o formulário de ajuste se a minuta foi gerada com sucesso
        # E se 'texto_pdfs_original' estiver na sessão (indicando que um upload válido ocorreu)
        if not minuta_completa_texto.startswith("Erro:") and 'texto_pdfs_original' in session:
            html_display += f"""
            <div class="section adjust-section"><h2>3. 🔧 Solicitar Ajustes na Minuta</h2>
            <form method="POST" action="/"><input type="hidden" name="action" value="ajustar_minuta">
            {''''''}
            <label for="instrucoes_ajuste">💡 Instruções para ajuste:</label>
            <textarea name="instrucoes_ajuste" rows="5" placeholder="Ex: Reforce argumento X, adicione jurisprudência Y..."></textarea>
            <input type="submit" value="🔄 Refazer Minuta com Ajustes" class="btn" style="margin-top: 20px;"></form></div>"""
        return html_display

# --- Instâncias ---
minuta_generator_instance = MinutaGenerator(model) 
pdf_processor_instance = PDFProcessor() 
minuta_parser_instance = MinutaParser() 
html_generator_instance = HTMLGenerator() 

# --- Rotas Flask ---
@app.route("/", methods=["GET", "POST"])
def api_root():
    if request.method == "POST":
        # A lógica de _handle_post_request_api determinará a ação (upload ou ajuste)
        return _handle_post_request_api()
    
    # Para GET na raiz, podemos retornar uma mensagem de status da API
    logger.info(f"API GET / status check. Session ID: {session.sid if hasattr(session, 'sid') else 'N/A'}")
    return jsonify(message="API do Gerador de Contestações PGE-MS está online e pronta.",
                   model_status=f"Modelo Gemini '{ACTUAL_MODEL_NAME_LOADED}' {'carregado' if model else 'NÃO CARREGADO'}",
                   session_backend="Flask-Session (filesystem)"
                   ), 200

def _handle_post_request_api():
    action = request.form.get("action") # O frontend React enviará 'action' no FormData ou URLSearchParams
    logger.debug(f"API POST / Action: {action}. Session ID: {session.sid if hasattr(session, 'sid') else 'N/A'}")

    if not model: # Checagem crucial antes de qualquer ação que dependa do modelo
        logger.error("API: Tentativa de ação POST sem modelo Gemini carregado.")
        return jsonify({"success": False, "error": "Erro crítico: O serviço de IA não está configurado no servidor."}), 503 # Service Unavailable

    if action == "upload_pdfs":
        return _handle_upload_pdfs_api()
    elif action == "ajustar_minuta":
        return _handle_ajustar_minuta_api()
    
    logger.warning(f"API: Ação POST desconhecida ou ausente: '{action}'")
    return jsonify({"success": False, "error": "Ação inválida ou não especificada."}), 400

def _handle_upload_pdfs_api():
    logger.info("API: Iniciando processamento de upload de PDFs.")
    # Limpa a sessão ANTES de processar um novo upload para evitar acúmulo de dados antigos.
    # Mas guarda o que for preciso para o frontend se necessário (embora o frontend agora gerencie mais estado).
    # Com Flask-Session, session.clear() limpa os dados do lado do servidor para este usuário.
    session.clear() 
    
    if 'pdfs' not in request.files:
        logger.warning("API Upload: Nenhum arquivo PDF enviado (chave 'pdfs' ausente).")
        return jsonify({"success": False, "error": "Nenhum arquivo PDF enviado."}), 400
    
    files = request.files.getlist('pdfs')
    if not files or all(f.filename == '' for f in files):
        logger.warning("API Upload: Nenhum arquivo PDF selecionado (lista vazia ou nomes vazios).")
        return jsonify({"success": False, "error": "Nenhum arquivo PDF selecionado."}), 400
    
    if len(files) > MAX_FILES:
        logger.warning(f"API Upload: Excedido o número máximo de arquivos ({len(files)} > {MAX_FILES}).")
        return jsonify({"success": False, "error": f"Por favor, envie no máximo {MAX_FILES} arquivos."}), 400
    
    valid_files, val_errors = [], []
    for f in files:
        s_fn = secure_filename(f.filename) if f and f.filename else "ArquivoDesconhecido"
        if f and f.filename and pdf_processor_instance.allowed_file(f.filename):
            f.seek(0, os.SEEK_END); f_size = f.tell(); f.seek(0, os.SEEK_SET)
            if f_size > MAX_FILE_SIZE: 
                val_errors.append(f"Arquivo '{s_fn}' ({(f_size/(1024*1024)):.1f}MB) excede o limite de {(MAX_FILE_SIZE/(1024*1024)):.0f}MB.")
            else: 
                valid_files.append(f)
        elif f and f.filename: 
            val_errors.append(f"Arquivo '{s_fn}' não é um PDF válido.")

    if val_errors:
         logger.warning(f"API Upload: Erros de validação de arquivos: {val_errors}")
         return jsonify({"success": False, "error": " ".join(val_errors), "warnings":None}), 400 # Bad Request

    if not valid_files:
        logger.warning("API Upload: Nenhum arquivo PDF válido fornecido após a filtragem.")
        return jsonify({"success": False, "error": "Nenhum arquivo PDF válido foi fornecido.", "warnings":None}), 400
        
    texto_pdfs, filenames, extract_errors = pdf_processor_instance.extract_text_from_pdfs(valid_files)
    
    current_warnings = [] # Inicializa lista de avisos para esta requisição
    if extract_errors: 
        current_warnings.extend(extract_errors)
        logger.warning(f"API Upload: Erros durante a extração de texto dos PDFs: {extract_errors}")

    if not texto_pdfs:
        error_message = "Não foi possível extrair texto dos PDFs enviados."
        if extract_errors: 
            error_message += f" Detalhes: {'; '.join(extract_errors)}"
        logger.error(f"API Upload: {error_message}")
        return jsonify({"success": False, "error": error_message, "warnings": current_warnings}), 400
    
    # Salva na sessão (lado do servidor com Flask-Session)
    session['texto_pdfs_original'] = texto_pdfs 
    session['filenames_processados'] = filenames
    # Warnings podem ser retornados na resposta JSON se relevante

    logger.info("API Upload: Texto extraído. Chamando o gerador de minutas.")
    minuta_gerada = minuta_generator_instance.generate_minuta(texto_pdfs)
    
    if isinstance(minuta_gerada, str) and minuta_gerada.startswith("Erro:"):
        logger.error(f"API Upload: Erro na geração da minuta pela IA: {minuta_gerada}")
        # Retorna o erro da IA, mas também os warnings da extração de PDF, se houverem.
        return jsonify({"success": False, "error": minuta_gerada, "warnings": current_warnings}), 500 # Internal Server Error ou Bad Gateway (502) se for erro da IA
    else:
        session['minuta_gerada'] = minuta_gerada # Salva a minuta gerada na sessão
        logger.info("API Upload: Minuta gerada com sucesso.")
        return jsonify({
            "success": True, 
            "message": "Minuta gerada com sucesso!",
            "minutaGerada": minuta_gerada, # Envia a minuta para o frontend
            "filenamesProcessados": filenames,
            "warnings": current_warnings # Envia quaisquer warnings de extração
        }), 200

def _handle_ajustar_minuta_api():
    logger.info("API: Iniciando ajuste de minuta.")
    instrucoes = request.form.get("instrucoes_ajuste", "").strip()
    
    # Com Flask-Session, 'texto_pdfs_original' é lido da sessão do servidor.
    texto_original_final = session.get("texto_pdfs_original")

    if not texto_original_final:
        logger.warning("API Ajuste: Texto original para ajuste não encontrado na sessão.")
        return jsonify({"success": False, "error": "Sessão expirada ou texto original não encontrado. Faça um novo upload."}), 400

    if not instrucoes:
        logger.warning("API Ajuste: Tentativa de ajuste sem instruções.")
        return jsonify({"success": False, "error": "Por favor, forneça instruções para o ajuste."}), 400
    
    # A checagem 'if not model:' já foi feita em _handle_post_request_api
    
    logger.info(f"API Ajuste: Ajustando minuta com instruções: '{instrucoes[:100]}...'")
    nova_minuta = minuta_generator_instance.generate_minuta(texto_original_final, instructions=instrucoes)
    
    if isinstance(nova_minuta, str) and nova_minuta.startswith("Erro:"):
        logger.error(f"API Ajuste: Erro no ajuste da minuta pela IA: {nova_minuta}")
        return jsonify({"success": False, "error": f"Falha no ajuste: {nova_minuta}"}), 500
    else:
        session['minuta_gerada'] = nova_minuta # Atualiza a minuta na sessão do servidor
        logger.info("API Ajuste: Minuta ajustada com sucesso.")
        return jsonify({
            "success": True, 
            "message": "Minuta ajustada com sucesso!",
            "minutaGerada": nova_minuta, # Envia a nova minuta para o frontend
            "filenamesProcessados": session.get('filenames_processados', []) # Reenvia os nomes dos arquivos
        }), 200

# --- Tratamento de Erros HTTP (adaptados para retornar JSON) ---
@app.errorhandler(404)
def not_found_error_api(error): 
    logger.warning(f"API 404: {request.url} - {error}")
    return jsonify(success=False, error="Recurso não encontrado.", message="A URL solicitada não foi encontrada no servidor."), 404

@app.errorhandler(500)
def internal_error_api(error): 
    logger.error(f"API 500: {error}", exc_info=True)
    return jsonify(success=False, error="Erro interno do servidor.", message="Ocorreu um erro inesperado no servidor. Tente novamente mais tarde."), 500

@app.errorhandler(413) # Payload Too Large (ex: se o upload de arquivos for muito grande)
def too_large_error_api(error): 
    logger.warning(f"API 413: Payload muito grande. Content length: {request.content_length} - {error}")
    # A configuração de MAX_CONTENT_LENGTH do Flask pode ser usada para limitar uploads
    # app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Ex: 16MB
    max_mb = app.config.get('MAX_CONTENT_LENGTH', MAX_FILES * MAX_FILE_SIZE) / (1024*1024) 
    return jsonify(success=False, error=f"Conteúdo da requisição muito grande. Limite aproximado: {max_mb:.1f} MB."), 413

# --- Execução da Aplicação ---
# (O bloco if __name__ == "__main__": permanece o mesmo)
if __name__ == "__main__":
    if not model: 
        print("*"*80 + "\nATENÇÃO: MODELO GEMINI NÃO CARREGADO. VERIFIQUE 'GEMINI_API_KEY' E LOGS.\n" + "*"*80)
    else:
        print(f"Modelo Gemini '{ACTUAL_MODEL_NAME_LOADED}' carregado. Aplicação pronta.")
        print(f"Sessões serão armazenadas em: {app.config['SESSION_FILE_DIR']}")
        print(f"Servidor Flask em http://127.0.0.1:{os.environ.get('PORT', 5000)}")
        print(f"Debug mode: {app.debug}. CTRL+C para sair.")
    app.run(debug=(os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'), host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

