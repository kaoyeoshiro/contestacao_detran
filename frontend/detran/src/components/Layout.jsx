// src/components/Layout.jsx
import React from 'react';

// Assumindo que 'logo-pge-branco.png' está na pasta 'public' do seu projeto Vite.
// Se você moveu para 'src/assets', o import seria: import logoPgeUrl from '../assets/logo-pge-branco.png';
const logoPgeUrl = '/logo-pge-branco.png'; // Caminho relativo à pasta 'public'

const Layout = ({ children, onNewAnalysis }) => {
  return (
    <div className="min-h-screen flex flex-col bg-dark-bg text-dark-text-primary font-sans selection:bg-pge-laranja selection:text-white">
      <header className="bg-dark-bg-secondary sticky top-0 z-50 shadow-2xl">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20"> {/* Altura do header */}
            <div className="flex items-center">
              <img
                src={logoPgeUrl}
                alt="Logo PGE-MS"
                className="h-12 w-auto" // Ajuste conforme necessário
              />
              {/* Exemplo de título ao lado do logo, se desejar: */}
              {/* <span className="ml-4 font-display text-2xl font-bold text-pge-ciano">Gerador IA</span> */}
            </div>
            <button
              onClick={onNewAnalysis}
              type="button" // Adicionado type="button" para clareza
              className="px-5 py-2.5 border-2 border-pge-ciano text-pge-ciano rounded-lg 
                         hover:bg-pge-ciano hover:text-dark-bg-secondary 
                         focus:ring-4 focus:ring-pge-ciano focus:ring-opacity-50
                         transition-all duration-200 ease-in-out font-display font-semibold text-sm tracking-wider"
            >
              NOVA ANÁLISE
            </button>
          </div>
        </div>
      </header>

      <main className="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-8"> {/* Adicionado padding ao main e container */}
        {children}
      </main>

      <footer className="bg-dark-bg-secondary text-dark-text-secondary text-center py-8">
        <p className="text-sm">&copy; {new Date().getFullYear()} LAB-PGE Inovação e Tecnologia - PGE MS</p>
        <p className="text-xs mt-1">Gerador de Contestações IA - Versão Frontend Moderna (React + Tailwind)</p>
      </footer>
    </div>
  );
};

export default Layout;