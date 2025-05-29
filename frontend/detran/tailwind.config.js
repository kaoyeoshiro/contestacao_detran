/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // Garante que o Tailwind procure em todos os arquivos relevantes
  ],
  theme: {
    extend: {
      colors: {
        'pge-azul': '#294964',
        'pge-laranja': '#F58634',
        'pge-ciano': '#51A8B1',
        // Cores para o tema escuro inspirado na sua referência
        'dark-bg': '#111827', // Um cinza bem escuro, quase preto
        'dark-bg-secondary': '#1F2937', // Um tom um pouco mais claro para cards/seções
        'dark-text-primary': '#F3F4F6', // Cinza bem claro para texto principal
        'dark-text-secondary': '#9CA3AF', // Cinza para texto secundário
      },
      fontFamily: {
        // Sugestão de fontes (precisarão ser importadas no index.html)
        sans: ['Inter', 'system-ui', 'Avenir', 'Helvetica', 'Arial', 'sans-serif'],
        display: ['Poppins', 'system-ui', 'Avenir', 'Helvetica', 'Arial', 'sans-serif'], // Para títulos
      },
    },
  },
  plugins: [],
}