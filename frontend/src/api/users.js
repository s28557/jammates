import { apiRequest } from './apiClient.js'

// current user profile
export function getCurrentUser() {
  return apiRequest('/users/me')
}
