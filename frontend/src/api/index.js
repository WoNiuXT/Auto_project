const BASE = '/api'

async function request(url, options = {}) {
  const res = await fetch(BASE + url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'HTTP ' + res.status)
  }
  return res.json()
}

export const api = {
  getStatus: () => request('/status'),
  getConfig: () => request('/config'),
  scrapeTopics: (data = {}) => request('/scrape', { method: 'POST', body: JSON.stringify(data) }),
  generateScript: (data) => request('/script', { method: 'POST', body: JSON.stringify(data) }),
  listScripts: () => request('/scripts'),
  getScript: (filename) => request('/scripts/' + filename),
  generateImages: (data = {}) => request('/images', { method: 'POST', body: JSON.stringify(data) }),
  listImages: () => request('/images'),
  selectImage: (data) => request('/review/select', { method: 'POST', body: JSON.stringify(data) }),
  publish: (data) => request('/publish', { method: 'POST', body: JSON.stringify(data) }),
  checkCookies: () => request('/cookies'),
}