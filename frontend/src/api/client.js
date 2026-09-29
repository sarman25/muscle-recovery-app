const API_BASE_URL = "https://muscle-recovery-app.onrender.com/api/v1";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail || `Ошибка запроса: ${response.status}`);
  }

  return response.json();
}

export function getHeatmap(telegramId) {
  return request(`/heatmap/${telegramId}`);
}

export function getProfile(telegramId) {
  return request(`/profile/${telegramId}`);
}

export function createProfile(data) {
  return request(`/profile`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getExercises() {
  return request(`/exercises`);
}

export function logWorkout(data) {
  return request(`/workouts`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}