import { apiRequest } from './apiClient.js'

// circle read requests
export function getMyCircles() {
  return apiRequest('/circles/my')
}

export function getCircleMembers(circleId) {
  return apiRequest(`/circles/${circleId}/members`)
}

// circle profile updates
export function updateCircleImage(circleId, imageUrl) {
  const params = new URLSearchParams()
  if (imageUrl.trim()) {
    params.set('image_url', imageUrl.trim())
  }

  return apiRequest(`/circles/${circleId}/image?${params.toString()}`, {
    method: 'PATCH',
  })
}

export function uploadCircleImage(circleId, file) {
  const formData = new FormData()
  formData.append('image', file)

  return apiRequest(`/circles/${circleId}/image/upload`, {
    method: 'POST',
    body: formData,
  })
}

export function updateCircleName(circleId, name) {
  const params = new URLSearchParams({ name })

  return apiRequest(`/circles/${circleId}/name?${params.toString()}`, {
    method: 'PATCH',
  })
}

// circle membership actions
export function leaveCircle(circleId) {
  return apiRequest(`/circles/${circleId}/leave`, {
    method: 'DELETE',
  })
}

export function removeCircleMember(circleId, userId) {
  return apiRequest(`/circles/${circleId}/members/${userId}`, {
    method: 'DELETE',
  })
}

export function deleteCircle(circleId) {
  return apiRequest(`/circles/${circleId}`, {
    method: 'DELETE',
  })
}

// circle create and join actions
export function createCircle(name) {
  const params = new URLSearchParams({ name })
  return apiRequest(`/circles?${params.toString()}`, {
    method: 'POST',
  })
}

export function joinCircle(inviteCode) {
  const params = new URLSearchParams({ invite_code: inviteCode })
  return apiRequest(`/circles/join?${params.toString()}`, {
    method: 'POST',
  })
}
