# Gerador de Contestações IA - PGE MS

Este projeto é uma aplicação web desenvolvida para a Procuradoria-Geral do Estado de Mato Grosso do Sul (PGE-MS) com o objetivo de automatizar a geração de minutas de contestações jurídicas. A ferramenta permite o upload de documentos PDF (como petições iniciais e documentos complementares), que são processados por uma Inteligência Artificial (Google Gemini) para redigir uma minuta de contestação estruturada.

## ✨ Funcionalidades

* Upload de múltiplos arquivos PDF (petição inicial + documentos).
* Extração de texto dos PDFs.
* Integração com a API do Google Gemini para análise e geração de texto jurídico.
* Exibição da minuta de contestação formatada em uma interface moderna.
* Funcionalidade para solicitar ajustes na minuta gerada.
* Interface de usuário responsiva com tema escuro.

## 🚀 Tecnologias Utilizadas

**Backend:**
* Python 3.x
* Flask (para a API e servidor web)
* Flask-Session (para gerenciamento de sessões no lado do servidor)
* Flask-CORS (para permitir requisições do frontend)
* `google-generativeai` (SDK do Google para a API Gemini)
* PyMuPDF (para extração de texto de PDFs)

**Frontend:**
* React (com Vite para o ambiente de desenvolvimento)
* Tailwind CSS (para estilização)
* Axios (para chamadas HTTP à API backend)
* `react-dropzone` (para a funcionalidade de upload de arquivos com drag-and-drop)
* `interweave` (para renderizar HTML de forma segura)
* `markupsafe` (indiretamente, para garantir a segurança na renderização de HTML, se necessário)

## 📁 Estrutura do Projeto

O projeto é dividido em duas pastas principais:

* `backend/`: Contém a aplicação Flask (API Python).
* `frontend/`: Contém a aplicação React (Interface do Usuário).

## 🛠️ Setup e Instalação

### Pré-requisitos
* Node.js (versão LTS recomendada, que inclui npm) ou Yarn
* Python (versão 3.8 ou superior) e Pip

### Configuração do Backend

1.  **Navegue até a pasta do backend:**
    ```bash
    cd backend
    ```
2.  **Crie e ative um ambiente virtual Python:**
    ```bash
    python -m venv venv
    # No Windows:
    .\venv\Scripts\activate
    # No macOS/Linux:
    source venv/bin/activate
    ```
3.  **Instale as dependências Python:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure as Variáveis de Ambiente:**
    * `GEMINI_API_KEY`: Sua chave da API do Google Gemini.
        * Ex (Linux/macOS): `export GEMINI_API_KEY="SUA_CHAVE_AQUI"`
        * Ex (Windows PowerShell): `$env:GEMINI_API_KEY="SUA_CHAVE_AQUI"`
    * `FLASK_SECRET_KEY`: Uma chave secreta forte para o Flask (usada para assinar sessões, etc.). Você pode gerar uma com `python -c 'import os; print(os.urandom(24).hex())'`.
        * Ex (Linux/macOS): `export FLASK_SECRET_KEY="SUA_CHAVE_SECRETA_FORTE"`
        * Ex (Windows PowerShell): `$env:FLASK_SECRET_KEY="SUA_CHAVE_SECRETA_FORTE"`

    *Opcional: Crie um arquivo `.env` na pasta `backend` e use a biblioteca `python-dotenv` para carregar essas variáveis (não implementado no código atual, mas é uma boa prática).*

### Configuração do Frontend

1.  **Navegue até a pasta do frontend:**
    ```bash
    cd frontend 
    # (ou o nome que você deu, ex: pge-contestacao-frontend, detran)
    ```
2.  **Instale as dependências do Node.js:**
    ```bash
    npm install
    # ou, se você usa Yarn:
    # yarn install
    ```
3.  **Configure a URL do backend para o Vite:**
    Copie o arquivo `.env.example` para `.env` dentro da pasta `frontend` e ajuste o valor de `VITE_API_BASE_URL` caso o endereço do backend seja diferente de `http://localhost:5000`.

## ▶️ Executando a Aplicação

Você precisará de dois terminais abertos para rodar o backend e o frontend simultaneamente.

1.  **Inicie o Servidor Backend (Flask):**
    * No terminal, na pasta `backend/` e com o ambiente virtual ativado:
        ```bash
        python contestacao.py
        ```
    * O backend estará rodando (por padrão) em `http://localhost:5000`.
      Defina essa URL em `VITE_API_BASE_URL` caso utilize outro endereço.

2.  **Inicie o Servidor Frontend (React/Vite):**
    * No outro terminal, na pasta `frontend/`:
        ```bash
        npm run dev
        # ou, se você usa Yarn:
        # yarn dev
        ```
    * O frontend estará acessível (por padrão) em `http://localhost:5173` (o Vite informará a URL exata).

3.  **Acesse a Aplicação:**
    * Abra a URL do frontend (ex: `http://localhost:5173`) no seu navegador.

## 🎨 Design e Estilo
* O frontend utiliza um tema escuro inspirado na referência visual fornecida.
* As cores institucionais da PGE-MS (Azul `#294964`, Laranja `#F58634`, Ciano `#51A8B1`) são usadas como acentos.
* O logo da PGE-MS (versão branca) é exibido no header. Certifique-se de que o arquivo
  `logo-pge-branco.png` esteja presente em `frontend/detran/public/` ou ajuste o
  caminho definido no componente `Layout.jsx`.
* Fontes: Inter (corpo) e Poppins (títulos).

## 🔮 Próximos Passos / Melhorias Futuras (Sugestões)
* Implementar autenticação de usuários.
* Salvar histórico de minutas geradas.
* Opção para editar a minuta diretamente na interface.
* Melhorar o tratamento de erros e feedback ao usuário.
* Deploy da aplicação.

---
