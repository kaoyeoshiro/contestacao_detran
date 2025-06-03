// src/components/UploadScreen.jsx
import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios'; // Para chamadas HTTP

// URL base da API definida via variável de ambiente do Vite
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// Ícone de Upload (SVG Tailwind-friendly)
const UploadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="mx-auto h-16 w-16 text-gray-500 group-hover:text-pge-ciano transition-colors">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l-3.75 3.75M12 9.75l3.75 3.75M3 17.25V6.75A2.25 2.25 0 015.25 4.5h13.5A2.25 2.25 0 0121 6.75v10.5A2.25 2.25 0 0118.75 21H5.25A2.25 2.25 0 013 17.25z" />
  </svg>
);

const UploadScreen = ({ onMinutaResponse, setIsLoading, isLoading, setError }) => {
  const [files, setFiles] = useState([]);

  const onDrop = useCallback(acceptedFiles => {
    const currentFileCount = files.length;
    // Limita o número de novos arquivos para não exceder 5 no total
    const newFilesPotential = acceptedFiles.slice(0, 5 - currentFileCount);

    const pdfFiles = newFilesPotential.filter(
      file => file.type === "application/pdf" || file.name.toLowerCase().endsWith('.pdf')
    );
    
    if (pdfFiles.length !== newFilesPotential.length && newFilesPotential.length > 0) {
        setError("Apenas arquivos PDF são permitidos. Alguns arquivos foram ignorados.");
    }
    if (currentFileCount + pdfFiles.length > 5 && pdfFiles.length > 0) { // Adiciona esta verificação
        setError("Você pode enviar no máximo 5 arquivos no total. Alguns arquivos foram ignorados.");
    }
    // Adiciona os novos arquivos válidos, garantindo que não exceda 5
    setFiles(prevFiles => [...prevFiles, ...pdfFiles].slice(0, 5));
  }, [files, setError]); // Adicionado setError às dependências do useCallback

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 5, // O react-dropzone já lida com isso, mas a lógica acima é um controle extra
    multiple: true,
    noClick: true, 
    noKeyboard: true,
  });

  const removeFile = (fileName) => {
    setFiles(prevFiles => prevFiles.filter(file => file.name !== fileName));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (files.length === 0) {
      setError("Por favor, selecione pelo menos um arquivo PDF.");
      return;
    }
    setIsLoading(true);
    setError(''); 

    const formData = new FormData();
    files.forEach(file => {
      formData.append('pdfs', file); 
    });
    formData.append('action', 'upload_pdfs'); // O backend espera esta ação

    try {
      const response = await axios.post(
        `${API_BASE_URL}/`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          withCredentials: true
        }
      );
      onMinutaResponse(response.data);
    } catch (err) {
      console.error("Erro no upload/geração da minuta:", err);
      let errorMessage = "Falha ao conectar com o servidor ou gerar minuta.";
      if (err.response && err.response.data && err.response.data.error) {
        errorMessage = err.response.data.error;
      } else if (err.message) {
        errorMessage = err.message;
      }
      // Passa um objeto de erro consistente para onMinutaResponse
      onMinutaResponse({ 
        success: false, 
        error: errorMessage, 
        warnings: err.response?.data?.warnings 
      });
    }
    // setIsLoading(false); // Movido para dentro de handleMinutaResponse em App.jsx
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16">
      <div className="text-center mb-10 sm:mb-16">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-pge-ciano via-pge-azul to-pge-laranja animate-gradient-x">
          Gerador de Contestações IA
        </h1>
        <p className="mt-4 sm:mt-6 text-lg sm:text-xl text-dark-text-secondary max-w-2xl mx-auto">
          Anexe a petição inicial e documentos complementares (PDFs). A inteligência artificial irá analisar e redigir uma minuta de contestação.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="max-w-3xl mx-auto bg-dark-bg-secondary p-6 sm:p-8 rounded-xl shadow-2xl">
        <div 
          {...getRootProps()} 
          className={`group mt-1 flex flex-col items-center justify-center px-6 pt-8 pb-8 border-2 ${isDragActive ? 'border-pge-laranja shadow-lg scale-105' : 'border-gray-600'} border-dashed rounded-lg cursor-pointer hover:border-pge-azul transition-all duration-300 ease-in-out`}
        >
          <input {...getInputProps()} />
          <UploadIcon />
          {isDragActive ? (
            <p className="mt-2 text-lg font-semibold text-pge-laranja">Solte os arquivos aqui!</p>
          ) : (
            <>
              <p className="mt-2 text-md text-dark-text-primary">
                Arraste e solte os PDFs aqui, ou
              </p>
              <button 
                type="button" 
                onClick={open} 
                className="mt-2 font-semibold text-pge-ciano hover:text-pge-azul transition-colors focus:outline-none"
              >
                selecione os arquivos
              </button>
            </>
          )}
          <p className="mt-2 text-xs text-dark-text-secondary">PDF até 10MB cada, máximo 5 arquivos.</p>
        </div>

        {files.length > 0 && (
          <div className="mt-8">
            <h3 className="text-xl font-medium text-dark-text-primary mb-3">Arquivos Selecionados:</h3>
            <ul className="space-y-2">
              {files.map(file => (
                <li key={file.name} className="px-3 py-2.5 bg-dark-bg rounded-md flex items-center justify-between text-sm shadow">
                  <div className="w-0 flex-1 flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-pge-laranja mr-2 flex-shrink-0">
                      <path fillRule="evenodd" d="M15.994 4.503a.75.75 0 00-.75-.75h-7.5a.75.75 0 000 1.5h7.5a.75.75 0 00.75-.75zM8.244 8.25a.75.75 0 000 1.5h7.5a.75.75 0 000-1.5h-7.5zM4.5 6.375a.75.75 0 01.75-.75h.008a.75.75 0 01.75.75v1.886c0 .48-.13.94-.372 1.342l-.243.405a.75.75 0 01-1.274-.764l.243-.405c.05-.083.076-.17.076-.26V6.375zm1.5 0A.75.75 0 004.5 5.625H3.75a.75.75 0 00-.75.75v10.5c0 .414.336.75.75.75h12.5a.75.75 0 00.75-.75V6.375a.75.75 0 00-.75-.75H6z" clipRule="evenodd" />
                    </svg>
                    <span className="ml-1 flex-1 w-0 truncate text-dark-text-secondary">{file.name} <span className="text-xs text-gray-500">({(file.size / 1024).toFixed(1)} KB)</span></span>
                  </div>
                  <div className="ml-4 flex-shrink-0">
                    <button 
                      type="button" 
                      onClick={() => removeFile(file.name)} 
                      className="font-medium text-red-500 hover:text-red-400 transition-colors"
                    >
                      Remover
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-10 text-center">
          <button
            type="submit"
            disabled={isLoading || files.length === 0}
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
                Analisando e Gerando...
              </>
            ) : (
              'Analisar e Gerar Minuta'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default UploadScreen;