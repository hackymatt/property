import axios from "axios";
import type { Domain, ScraperSource, Job, Schedule, JobRunLog, ScheduleRunLog, Paginated } from "./types";

export type { Paginated };

const http = axios.create({ baseURL: "/api" });

http.interceptors.request.use((config) => {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  },
);

export const auth = {
  login: (username: string, password: string) =>
    http.post<{ token: string; username: string }>("/auth/login", {
      username,
      password,
    }),
};

type ListParams = Record<string, string | number>;

const crud = <T>(path: string) => ({
  list: (params?: ListParams) => http.get<Paginated<T>>(path, { params }),
  get: (id: number) => http.get<T>(`${path}/${id}`),
  create: (data: Partial<T>) => http.post<T>(path, data),
  update: (id: number, data: Partial<T>) => http.put<T>(`${path}/${id}`, data),
  patch: (id: number, data: Partial<T>) => http.patch<T>(`${path}/${id}`, data),
  remove: (id: number) => http.delete(`${path}/${id}`),
});

export const domains = crud<Domain>("/domains");
export const sources = crud<ScraperSource>("/sources");
export const jobs = crud<Job>("/jobs");
export const schedules = crud<Schedule>("/schedules");
export const runLogs = crud<JobRunLog>("/run-logs");
export const scheduleLogs = crud<ScheduleRunLog>("/schedule-logs");
