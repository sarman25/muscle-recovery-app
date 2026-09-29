import bodyFrontSvg from './body-front.svg?raw';
import bodyBackSvg from './body-back.svg?raw';

const MUSCLE_COLOR_DEFAULT = '#3a3a45';

// Соответствие: статус мышцы -> id SVG-фильтра свечения.
// Сами фильтры (glow-red/glow-orange/glow-green) уже встроены в <defs>
// внутри body-front.svg и body-back.svg — добавлять их повторно через JS
// не нужно (в старой версии файла их дублировали, теперь не дублируем).
const STATUS_TO_FILTER = {
  peak_fatigue: 'url(#glow-red)',
  recovering: 'url(#glow-orange)',
  recovered: 'url(#glow-green)',
};

// Мышцы красятся по id элементов <path> внутри самого SVG — НЕ по номеру
// по порядку в документе. Раньше здесь были хардкодные номера от какой-то
// старой версии файла, из-за чего подсвечивались не те мышцы, что
// тренировались (например, вместо груди красились пресс и плечи).
// У каждого актуального файла есть группа <g id="muscles-front">/
// <g id="muscles-back"> со своими path id; для парных мышц используется
// схема id / id_r (левая/правая сторона).
const FRONT_MUSCLE_IDS = [
  'chest', 'abs',
  'shoulders', 'shoulders_r',
  'biceps', 'biceps_r',
  'forearms', 'forearms_r',
  'legs', 'legs_r',
  'calves', 'calves_r',
];

const BACK_MUSCLE_IDS = [
  'back', 'back_lower',
  'shoulders', 'shoulders_r',
  'triceps', 'triceps_r',
  'forearms', 'forearms_r',
  'legs', 'legs_r',
  'calves', 'calves_r',
];

// Соответствие: muscle_group из API -> id-шники в конкретном SVG-виде.
// back_lower красится вместе с back — в API нет отдельной зоны для
// поясницы, вся спина в модели данных это одна мышечная группа.
const FRONT_MUSCLE_TO_IDS = {
  chest: ['chest'],
  abs: ['abs'],
  shoulders: ['shoulders', 'shoulders_r'],
  biceps: ['biceps', 'biceps_r'],
  forearms: ['forearms', 'forearms_r'],
  legs: ['legs', 'legs_r'],
  calves: ['calves', 'calves_r'],
};

const BACK_MUSCLE_TO_IDS = {
  back: ['back', 'back_lower'],
  shoulders: ['shoulders', 'shoulders_r'],
  triceps: ['triceps', 'triceps_r'],
  forearms: ['forearms', 'forearms_r'],
  legs: ['legs', 'legs_r'],
  calves: ['calves', 'calves_r'],
};

const VIEWS = {
  front: { svg: bodyFrontSvg, muscleIds: FRONT_MUSCLE_IDS, groupToIds: FRONT_MUSCLE_TO_IDS },
  back: { svg: bodyBackSvg, muscleIds: BACK_MUSCLE_IDS, groupToIds: BACK_MUSCLE_TO_IDS },
};

function findMuscleEl(svgElement, id) {
  // querySelector по id надёжнее, чем getElementById, — работает
  // одинаково для встроенного в HTML-страницу SVG во всех браузерах.
  return svgElement.querySelector(`#${id}`);
}

function resetMuscles(svgElement, muscleIds) {
  muscleIds.forEach((id) => {
    const el = findMuscleEl(svgElement, id);
    if (!el) return;
    el.setAttribute('fill', MUSCLE_COLOR_DEFAULT);
    el.removeAttribute('filter');
  });
}

export function renderBodySvg(container, view = 'front') {
  container.innerHTML = VIEWS[view].svg;
  const svgElement = container.querySelector('svg');

  resetMuscles(svgElement, VIEWS[view].muscleIds);

  return svgElement;
}

export function applyHeatmapToSvg(svgElement, heatmapData, view = 'front') {
  if (!svgElement || !heatmapData) return;

  const { muscleIds, groupToIds } = VIEWS[view];

  // сброс всех мышечных зон в дефолтный цвет без свечения
  resetMuscles(svgElement, muscleIds);

  // покраска мышц с реальными данными
  heatmapData.muscles.forEach((muscle) => {
    const ids = groupToIds[muscle.muscle_group];
    if (!ids) return; // этой мышцы нет на данном виде (например, triceps спереди)

    const glowFilter = STATUS_TO_FILTER[muscle.status];

    ids.forEach((id) => {
      const el = findMuscleEl(svgElement, id);
      if (!el) return;
      el.setAttribute('fill', muscle.color_hex);
      if (glowFilter) el.setAttribute('filter', glowFilter);
    });
  });
}