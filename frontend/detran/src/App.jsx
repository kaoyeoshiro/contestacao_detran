// src/App.jsx
import React, { useState } from 'react';
import Layout from './components/Layout';
import UploadScreen from './components/UploadScreen';
import ResultScreen from './components/ResultScreen';
// Se você tiver um App.css e quiser usá-lo para estilos globais mínimos, mantenha o import.
// Caso contrário, se o index.css com Tailwind for suficiente, pode remover ou deixar vazio.
// import './App.css'; 

function App() {
  const [minutaResult, setMinutaResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [processedFiles, setProcessedFiles] = useState([]);
  const [warnings, setWarnings] = useState([]); // Para avisos da API ou da aplicação

  // Chamado quando o backend retorna uma minuta (ou erro), tanto na geração inicial quanto no ajuste
  const handleMinutaResponse = (data) => {
    setIsLoading(false); // Garante que o loading pare
    if (data && data.success) { // Verifica se data e data.success existem
      setMinutaResult(data.minutaGerada);
      setProcessedFiles(data.filenamesProcessados || []);
      setError(''); // Limpa erros anteriores
      setWarnings(data.warnings || []);
      // Scroll para o topo para ver a mensagem de sucesso/aviso
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      setMinutaResult(null); // Limpa minuta anterior em caso de erro
      setError(data?.error || 'Ocorreu um erro desconhecido ao processar a solicitação.');
      setWarnings(data?.warnings || []);
      // Não limpar processedFiles aqui, pois o usuário pode querer ver quais arquivos foram enviados
      // e talvez tentar um ajuste se o erro não foi crítico com os arquivos em si.
      // Se o erro for de upload, processedFiles já estará vazio.
    }
  };

  // Chamado para reiniciar o fluxo para uma nova análise
  const handleNewAnalysis = () => {
    setMinutaResult(null);
    setError('');
    setProcessedFiles([]);
    setWarnings([]);
    setIsLoading(false); 
    // Aqui você poderia adicionar lógica para resetar o estado interno do UploadScreen,
    // por exemplo, limpando a lista de arquivos selecionados nele, se ele mantiver esse estado.
    // Uma forma é passar uma prop "key" que muda para o UploadScreen, forçando-o a remontar.
  };

  return (
    <Layout onNewAnalysis={handleNewAnalysis}>
      {/* Seção para exibir mensagens de erro globais */}
      {error && (
        <div className="container mx-auto my-4 p-4 bg-red-700 text-white border-2 border-red-800 rounded-lg shadow-lg animate-pulse_once">
          <strong className="font-semibold">Erro:</strong> {error}
        </div>
      )}

      {/* Seção para exibir avisos globais */}
      {warnings && warnings.length > 0 && (
        <div className="container mx-auto my-4 p-4 bg-yellow-500 text-black border-2 border-yellow-600 rounded-lg shadow-lg">
          <strong className="font-semibold">Avisos:</strong>
          <ul className="list-disc list-inside ml-4 mt-1">
            {warnings.map((warn, index) => <li key={index}>{warn}</li>)}
          </ul>
        </div>
      )}

      {/* Renderização condicional da tela de Upload ou da tela de Resultado */}
      {!minutaResult ? (
        <UploadScreen 
          onMinutaResponse={handleMinutaResponse} 
          setIsLoading={setIsLoading} 
          isLoading={isLoading}
          setError={setError} // Passa a função setError para que UploadScreen possa reportar erros de validação ou upload
        />
      ) : (
        <ResultScreen 
          initialMinuta={minutaResult} 
          filenames={processedFiles}
          setIsLoading={setIsLoading}
          isLoading={isLoading}
          onNewAnalysis={handleNewAnalysis} // Para o botão "Gerar Nova Minuta" dentro de ResultScreen
          setError={setError} // Para que ResultScreen possa reportar erros (ex: ao ajustar)
          setWarnings={setWarnings} // Para que ResultScreen possa adicionar warnings
          onMinutaAdjusted={handleMinutaResponse} // Reutiliza a mesma função para tratar a resposta do ajuste
        />
      )}
    </Layout>
  );
}

export default App;