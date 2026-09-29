import { createProfile } from '../api/client.js';

export function renderOnboardingForm(container, telegramId, onComplete) {
  container.innerHTML = `
    <form id="onboarding-form" class="onboarding-form">
      <h2>Расскажи о себе</h2>

      <label>
        Пол
        <select name="gender" required>
          <option value="male">Мужчина</option>
          <option value="female">Женщина</option>
        </select>
      </label>

      <label>
        Рост (см)
        <input type="number" name="height_cm" min="100" max="250" required />
      </label>

      <label>
        Вес (кг)
        <input type="number" name="weight_kg" min="30" max="300" required />
      </label>

      <label>
        Возраст
        <input type="number" name="age" min="12" max="100" required />
      </label>

      <label>
        Уровень подготовки
        <select name="level" required>
          <option value="beginner">Новичок</option>
          <option value="amateur">Любитель</option>
          <option value="advanced">Продвинутый</option>
        </select>
      </label>

      <button type="submit">Продолжить</button>
      <p id="onboarding-error" class="error"></p>
    </form>
  `;

  const form = container.querySelector('#onboarding-form');
  const errorEl = container.querySelector('#onboarding-error');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorEl.textContent = '';

    const formData = new FormData(form);
    const payload = {
      telegram_id: telegramId,
      gender: formData.get('gender'),
      height_cm: Number(formData.get('height_cm')),
      weight_kg: Number(formData.get('weight_kg')),
      age: Number(formData.get('age')),
      level: formData.get('level'),
    };

    try {
      const profile = await createProfile(payload);
      onComplete(profile);
    } catch (error) {
      errorEl.textContent = `Ошибка: ${error.message}`;
    }
  });
}