/** Pull the server's message out of an axios error, with a usable fallback. */
export function errorMessage(err: unknown, fallback = 'Something went wrong'): string {
  const response = (err as { response?: { data?: { message?: string }; status?: number } })?.response;
  if (response?.data?.message) return response.data.message;
  if (response?.status === 503) return 'You appear to be offline. Reconnect and try again.';
  if ((err as { message?: string })?.message === 'Network Error') return 'Cannot reach the server.';
  return fallback;
}
