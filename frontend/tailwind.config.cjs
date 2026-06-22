module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#102d2b',
        lime: '#c8ff69',
        mint: '#80dfbd',
        coral: '#ff8066',
        canvas: '#f3f1e8',
      },
      boxShadow: {
        soft: '0 18px 50px rgba(16, 45, 43, 0.08)',
        lift: '0 22px 60px rgba(16, 45, 43, 0.14)',
      },
    },
  },
  plugins: [],
}
