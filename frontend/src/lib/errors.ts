import axios from 'axios';
import type { ApiErrorBody } from '@/types';

export function getErrorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (axios.isAxiosError<ApiErrorBody>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return detail.map((d) => d.msg).join('; ');
    }
    if (!error.response) return 'Cannot reach the server. Check your connection.';
    return fallback;
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function getErrorStatus(error: unknown): number | null {
  return axios.isAxiosError(error) ? (error.response?.status ?? null) : null;
}
