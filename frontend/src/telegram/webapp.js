export const tg = window.Telegram?.WebApp;

export function initTelegramApp() {
  if (!tg) {
    console.warn("Telegram WebApp SDK не найден — открой это приложение через Telegram");
    return { initData: null, user: null };
  }

  tg.ready();
  tg.expand();

  return {
    initData: tg.initData,
    user: tg.initDataUnsafe?.user,
  };
}