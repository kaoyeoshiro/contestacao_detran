// src/components/ResultScreen.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Markup } from 'interweave'; // Para renderizar HTML de forma segura

// FUNÇÃO LOCAL PARA ESCAPAR HTML BÁSICO
// Esta função substitui a necessidade de importar 'escape' de 'markupsafe' no frontend.
function simpleEscape(text) {
  if (typeof text !== 'string') return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const ResultScreen = ({ 
  initialMinuta, 
  filenames, 
  setIsLoading, 
  isLoading, 
  onNewAnalysis, 
  setError, 
  setWarnings, 
  onMinutaAdjusted 
}) => {
  const [ajusteInstrucoes, setAjusteInstrucoes] = useState('');
  const [minutaAtual, setMinutaAtual] = useState(initialMinuta);

  useEffect(() => {
    setMinutaAtual(initialMinuta); 
  }, [initialMinuta]);

  const handleCopyToClipboard = () => {
    const contentElement = document.getElementById('minuta-content-display-actual');
    if (!contentElement) {
      alert('Erro: Não foi possível encontrar o conteúdo da minuta para cópia.');
      return;
    }
    
    // Para preservar quebras de linha como no display, usamos innerText
    // innerText tenta mimetizar o que é visualmente selecionável
    let textToCopy = contentElement.innerText || contentElement.textContent || "";
    
    navigator.clipboard.writeText(textToCopy).then(() => {
      alert('Texto da minuta copiado para a área de transferência!');
    }).catch(err => {
      console.error('Erro ao copiar minuta com navigator.clipboard: ', err);
      // Tenta um fallback mais simples se o navigator.clipboard falhar
      try {
        const textArea = document.createElement("textarea");
        textArea.value = textToCopy; // Usa o texto já processado por innerText
        textArea.style.position = "fixed"; // Previne scroll
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        alert('Texto da minuta copiado (usando fallback)!');
      } catch (fallbackErr) {
        alert('Falha ao copiar minuta. Por favor, tente selecionar e copiar manualmente (Ctrl+C / Cmd+C).');
        console.error('Erro ao copiar minuta com fallback execCommand: ', fallbackErr);
      }
    });
  };
  
  // Função para formatar o texto para exibição HTML
  const transformTextToHtml = (text) => {
    if (!text) return "";

    // Normaliza quebras de linha primeiro
    let normalizedText = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    
    // 1. Escapa o texto INTEIRO primeiro usando nossa função local
    let html = simpleEscape(normalizedText); 
    // 2. Converte **texto** para <strong>texto</strong>. 
    //    O conteúdo $1 já foi escapado pela função simpleEscape, se continha <, >, &, etc.
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // 3. Converte quebras de linha (\n) para tags <br />
    html = html.replace(/\n/g, '<br />');
    return html;
  };

  const handleAjusteSubmit = async (event) => {
    event.preventDefault();
    if (!ajusteInstrucoes.trim()) {
      setError("Por favor, forneça instruções para o ajuste.");
      return;
    }
    setIsLoading(true);
    setError('');
    setWarnings([]); 

    try {
      const params = new URLSearchParams();
      params.append('action', 'ajustar_minuta');
      params.append('instrucoes_ajuste', ajusteInstrucoes);

      const response = await axios.post(
        'http://localhost:5000/',
        params,
        { withCredentials: true }
      );
      
      onMinutaAdjusted(response.data); 
      if(response.data.success) {
        setAjusteInstrucoes(''); 
      }

    } catch (err) {
      console.error("Erro ao ajustar minuta:", err);
      let errorMessage = "Falha ao conectar com o servidor ou ajustar minuta.";
      if (err.response && err.response.data && err.response.data.error) {
        errorMessage = err.response.data.error;
      } else if (err.message) {
        errorMessage = err.message;
      }
      onMinutaAdjusted({ 
        success: false, 
        error: errorMessage, 
        warnings: err.response?.data?.warnings,
        minutaGerada: minutaAtual 
      });
    }
    // setIsLoading(false); // Já é tratado em App.jsx pela onMinutaAdjusted (que é handleMinutaResponse)
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="bg-dark-bg-secondary p-6 sm:p-8 rounded-xl shadow-2xl">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
          <h2 className="text-3xl font-display font-bold text-pge-ciano mb-4 sm:mb-0">Minuta da Contestação Gerada</h2>
          {/* O botão "Nova Análise" principal está no Layout.jsx, mas se quiser um aqui:
          <button
            onClick={onNewAnalysis}
            className="px-4 py-2 border border-pge-laranja text-pge-laranja rounded-md hover:bg-pge-laranja hover:text-dark-bg-secondary transition-colors duration-150 font-medium text-sm"
          >
            Gerar Nova Análise
          </button>
          */}
        </div>

        {filenames && filenames.length > 0 && (
            <div className="mb-6 p-4 bg-dark-bg rounded-lg shadow">
                <h3 className="text-lg font-medium text-dark-text-primary">Com base nos arquivos:</h3>
                <ul className="list-disc list-inside text-dark-text-secondary ml-4 mt-1">
                    {filenames.map((name, idx) => <li key={idx}>{name}</li>)}
                </ul>
            </div>
        )}
        
        <div 
            id="minuta-content-display-actual" 
            className="prose prose-sm sm:prose-base prose-invert max-w-none p-4 sm:p-6 bg-dark-bg border border-gray-700 rounded-md min-h-[400px] max-h-[70vh] overflow-y-auto text-justify shadow-inner"
        >
          {/* A biblioteca Interweave fará a renderização segura do HTML gerado por transformTextToHtml */}
          <Markup content={transformTextToHtml(minutaAtual)} allowAttributes allowElements />
        </div>

        <div className="mt-8 text-center">
          <button
            onClick={handleCopyToClipboard}
            type="button"
            className="px-8 py-2.5 bg-pge-ciano text-white font-semibold rounded-lg hover:bg-opacity-80 focus:ring-4 focus:ring-pge-ciano focus:ring-opacity-50 transition-all duration-150 ease-in-out"
          >
            Copiar Texto da Minuta
          </button>
        </div>

        <div className="mt-12 pt-8 border-t border-gray-700">
          <h3 className="text-2xl font-display font-bold text-pge-laranja mb-6 text-center sm:text-left">Solicitar Ajustes na Minuta</h3>
          <form onSubmit={handleAjusteSubmit} className="max-w-xl mx-auto sm:mx-0">
            <div>
              <label htmlFor="instrucoes_ajuste" className="block text-md font-medium text-dark-text-secondary mb-2">
                Instruções para o ajuste:
              </label>
              <textarea
                id="instrucoes_ajuste"
                name="instrucoes_ajuste"
                rows="5"
                className="block w-full shadow-sm sm:text-sm border-gray-600 rounded-lg bg-dark-bg focus:ring-pge-laranja focus:border-pge-laranja text-dark-text-primary p-3 placeholder-gray-500"
                value={ajusteInstrucoes}
                onChange={(e) => setAjusteInstrucoes(e.target.value)}
                placeholder="Ex: Reforce o argumento sobre prescrição, adicione jurisprudência específica (STJ, TJMS)..."
              />
            </div>
            <div className="mt-8 text-center">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full sm:w-auto inline-flex justify-center items-center px-10 py-3 border border-transparent text-base font-semibold rounded-lg shadow-sm text-white 
                           bg-gradient-to-r from-pge-azul via-pge-ciano to-pge-azul hover:from-pge-azul hover:to-pge-ciano 
                           focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-dark-bg focus:ring-pge-laranja 
                           disabled:opacity-60 disabled:cursor-not-allowed 
                           transition-all duration-150 ease-in-out transform hover:scale-105"
              >
                {isLoading ? ( 
                    <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Ajustando Minuta...
                  </>
                ) : 'Refazer Minuta com Ajustes'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ResultScreen;