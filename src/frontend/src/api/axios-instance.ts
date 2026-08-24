import Axios, { AxiosError, AxiosRequestConfig } from "axios";

// Base URL lấy từ biến môi trường Vite khi build UI, mặc định backend cục bộ.
const baseURL =
  (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE ??
  "http://localhost:8000";

export const AXIOS_INSTANCE = Axios.create({ baseURL });

// Tự gắn JWT (lưu ở localStorage sau khi POST /auth/login) vào mọi request.
AXIOS_INSTANCE.interceptors.request.use((config) => {
  const token =
    typeof localStorage !== "undefined" ? localStorage.getItem("token") : null;
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Hết hạn hoặc 401 thì xóa token và đưa về màn đăng nhập.
AXIOS_INSTANCE.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login") window.location.assign("/login");
    }
    return Promise.reject(error);
  },
);

// Mutator mà Orval gọi cho từng endpoint.
export const customInstance = <T>(config: AxiosRequestConfig): Promise<T> => {
  return AXIOS_INSTANCE({ ...config }).then(({ data }) => data);
};

export type ErrorType<E> = AxiosError<E>;
export type BodyType<B> = B;
