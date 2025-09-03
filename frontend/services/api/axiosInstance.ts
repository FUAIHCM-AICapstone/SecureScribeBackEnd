import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';
const API_VERSION = 'v1';

const axiosInstance = axios.create({
    baseURL: `${API_BASE_URL}/${API_VERSION}`,
});

export { API_BASE_URL, API_VERSION };
export default axiosInstance;
