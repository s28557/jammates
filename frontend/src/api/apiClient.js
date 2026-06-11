const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
const AUTH_EXPIRED_EVENT = 'jammates:auth-expired'

function notifyAuthExpired() {
  localStorage.removeItem('jammates_token')
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT))
}

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem('jammates_token')
  const isFormData = options.body instanceof FormData
  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...options.headers,
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const message = await response.text()
    const error = new Error(message || `Request failed with status ${response.status}`)
    error.status = response.status

    if (response.status === 401) {
      notifyAuthExpired()
    }

    throw error
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

export { API_BASE_URL, AUTH_EXPIRED_EVENT }
