import { logWorkout, getExercises } from '../api/client.js';

const CATEGORIES = [
  { key: 'chest', emoji: '🏋️‍♂️', label: 'Грудь' },
  { key: 'back', emoji: '🏋️‍♀️', label: 'Спина' },
  { key: 'legs', emoji: '🦵', label: 'Ноги' },
  { key: 'shoulders', emoji: '🎯', label: 'Плечи' },
  { key: 'arms', emoji: '🦾', label: 'Руки' },
  { key: 'abs', emoji: '🔥', label: 'Пресс' },
  { key: 'cardio', emoji: '🏃‍♂️', label: 'Кардио' },
];

export async function renderWorkoutForm(container, telegramId, onComplete) {
  container.innerHTML = `<p style="text-align: center; color: #aaa;">Загружаем упражнения...</p>`;

  let exercisesList;
  try {
    exercisesList = await getExercises();
  } catch (error) {
    container.innerHTML = `<p style="color: red; text-align: center;">Ошибка: ${error.message}</p>`;
    return;
  }

  // состояние мастера
  let selectedCategory = null;
  let selectedExercise = null;
  let offsetHours = 0; // 0 = сегодня, -24 = вчера

  renderStep1();

  // ---------- ШАГ 1: выбор категории ----------
  function renderStep1() {
    container.innerHTML = `
      <h2 style="text-align:center;">Что тренируем?</h2>
      <div class="category-grid" id="category-grid"></div>
      <button type="button" id="skip-workout-btn" class="secondary-btn" style="margin-top: 20px;">Пропустить</button>
    `;

    const grid = container.querySelector('#category-grid');
    CATEGORIES.forEach((cat) => {
      const hasExercises = exercisesList.some((ex) => ex.category === cat.key);
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'category-card';
      card.disabled = !hasExercises;
      card.innerHTML = `<span class="category-emoji">${cat.emoji}</span><span>${cat.label}</span>`;
      card.addEventListener('click', () => {
        selectedCategory = cat.key;
        renderStep2();
      });
      grid.appendChild(card);
    });

    container.querySelector('#skip-workout-btn').addEventListener('click', () => onComplete());
  }

  // ---------- ШАГ 2: выбор упражнения ----------
  function renderStep2() {
    const categoryLabel = CATEGORIES.find((c) => c.key === selectedCategory)?.label || '';
    const filtered = exercisesList.filter((ex) => ex.category === selectedCategory);

    container.innerHTML = `
      <button type="button" id="back-to-categories" class="back-link">← Назад к категориям</button>
      <h2 style="text-align:center;">${categoryLabel}</h2>
      <div class="exercise-cards" id="exercise-cards"></div>
    `;

    container.querySelector('#back-to-categories').addEventListener('click', renderStep1);

    const cardsContainer = container.querySelector('#exercise-cards');
    filtered.forEach((ex) => {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'exercise-card';
      card.textContent = ex.name;
      card.addEventListener('click', () => {
        selectedExercise = ex;
        renderStep3();
      });
      cardsContainer.appendChild(card);
    });
  }

  // ---------- ШАГ 3: параметры и сохранение ----------
  function renderStep3() {
    const isCardio = selectedExercise.category === 'cardio';

    container.innerHTML = `
      <button type="button" id="back-to-exercises" class="back-link">← Назад к упражнениям</button>
      <h2 style="text-align:center;">${selectedExercise.name}</h2>

      <div class="date-toggle">
        <button type="button" class="date-toggle-btn active" data-offset="0">Сегодня</button>
        <button type="button" class="date-toggle-btn" data-offset="-24">Вчера</button>
      </div>

      <form id="params-form" class="workout-form">
        ${
          isCardio
            ? `
          <label>Время (минуты)
            <input type="number" name="duration_minutes" min="1" max="600" required />
          </label>
          <label>Дистанция (км)
            <input type="number" name="distance_km" min="0.1" max="200" step="0.1" />
          </label>
        `
            : `
          <label>Вес (кг)
            <input type="number" name="load_kg" min="0" max="500" value="0" />
          </label>
          <label>Подходы
            <input type="number" name="sets" min="1" max="20" required />
          </label>
          <label>Повторения
            <input type="number" name="reps" min="1" max="200" required />
          </label>
        `
        }
        <button type="submit" class="save-btn">🔥 Сохранить и покрасить мышцы</button>
        <p id="workout-error" class="error"></p>
      </form>
    `;

    container.querySelector('#back-to-exercises').addEventListener('click', renderStep2);

    const dateButtons = container.querySelectorAll('.date-toggle-btn');
    dateButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        dateButtons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        offsetHours = Number(btn.dataset.offset);
      });
    });

    const form = container.querySelector('#params-form');
    const errorEl = container.querySelector('#workout-error');

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      errorEl.textContent = '';

      const formData = new FormData(form);
      const exercisePayload = { exercise_id: selectedExercise.id };

      if (isCardio) {
        exercisePayload.duration_minutes = Number(formData.get('duration_minutes'));
        const distance = formData.get('distance_km');
        if (distance) exercisePayload.distance_km = Number(distance);
      } else {
        exercisePayload.sets = Number(formData.get('sets'));
        exercisePayload.reps = Number(formData.get('reps'));
        exercisePayload.load_kg = Number(formData.get('load_kg') || 0);
      }

      try {
        await logWorkout({
          telegram_id: telegramId,
          trained_at_offset_hours: offsetHours,
          exercises: [exercisePayload],
        });
        onComplete();
      } catch (error) {
        errorEl.textContent = `Ошибка: ${error.message}`;
      }
    });
  }
}