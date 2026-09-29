import './style.css';
import { initTelegramApp } from './telegram/webapp.js';
import { getHeatmap, getProfile } from './api/client.js';
import { renderBodySvg, applyHeatmapToSvg } from './body/svg-renderer.js';
import { renderOnboardingForm } from './ui/onboarding.js';
import { renderWorkoutForm } from './ui/workout-form.js';

const REFRESH_INTERVAL_MS = 30_000;

const { user } = initTelegramApp();

const TEST_TELEGRAM_ID = 123456789;
const telegramId = user?.id || TEST_TELEGRAM_ID;

const app = document.querySelector('#app');
let refreshTimerId = null;
let currentView = 'front';
let currentHeatmapData = null;

async function start() {
  try {
    await getProfile(telegramId);
    showHeatmapScreen();
  } catch (error) {
    renderOnboardingForm(app, telegramId, () => {
      showHeatmapScreen();
    });
  }
}

function showHeatmapScreen() {
  app.innerHTML = `
    <div style="text-align: center; margin-top: 20px;">
      <button id="view-front-btn" class="view-toggle-btn active">Спереди</button>
      <button id="view-back-btn" class="view-toggle-btn">Сзади</button>
    </div>
    <div id="body-container" style="width: 300px; margin: 20px auto;"></div>
    <p id="status" style="text-align: center; color: #aaa;">Загружаем данные...</p>
    <div style="text-align: center;">
      <button id="log-workout-btn" class="secondary-btn">+ Записать тренировку</button>
    </div>
  `;

  const bodyContainer = document.querySelector('#body-container');
  const statusEl = document.querySelector('#status');
  const logBtn = document.querySelector('#log-workout-btn');
  const frontBtn = document.querySelector('#view-front-btn');
  const backBtn = document.querySelector('#view-back-btn');

  currentView = 'front';
  let svgElement = renderBodySvg(bodyContainer, currentView);

  refreshHeatmap(svgElement, statusEl);

  if (refreshTimerId) clearInterval(refreshTimerId);
  refreshTimerId = setInterval(() => {
    refreshHeatmap(svgElement, statusEl);
  }, REFRESH_INTERVAL_MS);

  function switchView(view) {
    currentView = view;
    svgElement = renderBodySvg(bodyContainer, currentView);
    frontBtn.classList.toggle('active', view === 'front');
    backBtn.classList.toggle('active', view === 'back');

    if (currentHeatmapData) {
      applyHeatmapToSvg(svgElement, currentHeatmapData, currentView);
    }
  }

  frontBtn.addEventListener('click', () => switchView('front'));
  backBtn.addEventListener('click', () => switchView('back'));

  logBtn.addEventListener('click', () => {
    if (refreshTimerId) clearInterval(refreshTimerId);
    renderWorkoutForm(app, telegramId, () => {
      showHeatmapScreen();
    });
  });

  // сохраняем свежий svgElement для функции обновления через замыкание
  async function refreshHeatmap() {
    try {
      const data = await getHeatmap(telegramId);
      currentHeatmapData = data;
      applyHeatmapToSvg(svgElement, data, currentView);
      statusEl.style.color = '#aaa';
      statusEl.textContent = `Обновлено: ${new Date(data.generated_at).toLocaleTimeString()}`;
    } catch (error) {
      statusEl.style.color = 'red';
      statusEl.textContent = `Ошибка: ${error.message}`;
    }
  }
}

start();