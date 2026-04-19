import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 300_000, // 5 min — OCR on large PDFs can be slow
});

export default api;
