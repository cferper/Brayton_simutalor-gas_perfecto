/* Progressive enhancement; all sections/plots remain readable without JS. */
(() => {
  'use strict';
  const panels = [...document.querySelectorAll('.dashboard-panel')];
  if (!panels.length) return;
  document.documentElement.classList.add('js');
  const nav = [...document.querySelectorAll('.section-nav a')];
  function activateSection(id, focus = false) {
    const target = document.getElementById(id);
    if (!panels.includes(target)) return;
    panels.forEach(p => p.classList.toggle('active', p === target));
    nav.forEach(a => a.hash === '#' + id ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
    if (focus) target.querySelector('h2')?.focus({preventScroll: true});
    document.querySelector('.sidebar').classList.remove('menu-open');
    document.querySelector('.menu-toggle').setAttribute('aria-expanded', 'false');
  }
  function locationSection() {
    const [id, tab] = location.hash.slice(1).split('/');
    activateSection(id || document.body.dataset.initialSection || 'simulacion');
    if (tab) document.querySelector(`[data-plot-tab="${CSS.escape(tab)}"]`)?.click();
  }
  document.addEventListener('click', e => {
    const link = e.target.closest('a[href^="#"]');
    if (!link) return;
    const [id] = link.hash.slice(1).split('/');
    if (!panels.includes(document.getElementById(id))) return;
    e.preventDefault();
    history.pushState(null, '', link.hash);
    locationSection();
    document.getElementById(id).querySelector('h2')?.focus({preventScroll:true});
  });
  window.addEventListener('hashchange', locationSection);
  window.addEventListener('popstate', locationSection);
  document.querySelector('.menu-toggle').addEventListener('click', e => {
    const opened = document.querySelector('.sidebar').classList.toggle('menu-open');
    e.currentTarget.setAttribute('aria-expanded', String(opened));
  });
  document.querySelectorAll('[data-plot-viewer]').forEach(viewer => {
    const buttons = [...viewer.querySelectorAll('[data-plot-tab]')];
    const figures = [...viewer.querySelectorAll('figure')];
    function selectTab(button) {
      buttons.forEach(b => { b.setAttribute('aria-selected', String(b === button)); b.tabIndex = b === button ? 0 : -1; });
      figures.forEach(f => f.classList.toggle('plot-hidden', button.dataset.plotTab !== 'todas' && f.dataset.plotGroup !== button.dataset.plotTab));
      viewer.querySelector('.plot-grid').classList.toggle('single', figures.filter(f => !f.classList.contains('plot-hidden')).length === 1);
      viewer.querySelector('.plot-grid').setAttribute('aria-labelledby', button.id);
    }
    buttons.forEach((button, i) => {
      button.addEventListener('click', () => selectTab(button));
      button.addEventListener('keydown', e => {
        let index;
        if (e.key === 'ArrowRight') index = (i + 1) % buttons.length;
        if (e.key === 'ArrowLeft') index = (i - 1 + buttons.length) % buttons.length;
        if (e.key === 'Home') index = 0;
        if (e.key === 'End') index = buttons.length - 1;
        if (index !== undefined) { e.preventDefault(); buttons[index].focus(); selectTab(buttons[index]); }
      });
    });
    if (buttons.length) selectTab(buttons[0]);
  });
  // Las dos vistas usan el mismo DOM; nunca recalculan resultados.
  document.querySelectorAll('[data-edu-tabs]').forEach(group => {
    const buttons = [...group.querySelectorAll(':scope > .edu-tabbar > [role="tab"]')];
    const panes = buttons.map(b => document.getElementById(b.getAttribute('aria-controls')));
    function select(index, moveFocus = false) {
      buttons.forEach((button, i) => {
        button.setAttribute('aria-selected', String(i === index));
        button.tabIndex = i === index ? 0 : -1;
        panes[i].hidden = i !== index;
      });
      if (moveFocus) buttons[index].focus();
    }
    buttons.forEach((b,i) => {
      b.addEventListener('click', () => select(i));
      b.addEventListener('keydown', e => {
        let index = i;
        if (e.key === 'ArrowRight') index = (i+1)%buttons.length;
        else if (e.key === 'ArrowLeft') index = (i+buttons.length-1)%buttons.length;
        else if (e.key === 'Home') index = 0;
        else if (e.key === 'End') index = buttons.length-1;
        else return;
        e.preventDefault(); select(index,true);
      });
    });
    select(0);
  });
  const dialog = document.querySelector('.chart-dialog');
  let opener;
  function enlarge(figure, button) {
    if (typeof dialog.showModal !== 'function') return;
    opener = button;
    dialog.querySelector('h2').textContent = figure.querySelector('figcaption').textContent;
    const image = dialog.querySelector('img');
    image.src = figure.querySelector('img').src;
    image.alt = figure.querySelector('img').alt;
    dialog.showModal();
  }
  document.querySelectorAll('[data-plot-viewer] figure').forEach(figure => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'zoom-button'; button.textContent = 'Ampliar';
    button.setAttribute('aria-label', 'Ampliar: ' + figure.querySelector('figcaption').textContent);
    button.addEventListener('click', () => enlarge(figure, button));
    figure.append(button);
    figure.querySelector('img').addEventListener('click', () => enlarge(figure, button));
  });
  dialog.querySelector('button').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => { dialog.querySelector('img').removeAttribute('src'); opener?.focus(); });
  let printDetails = [];
  window.addEventListener('beforeprint', () => { printDetails = [...document.querySelectorAll('details:not([open])')]; printDetails.forEach(d => { d.open = true; }); });
  window.addEventListener('afterprint', () => printDetails.forEach(d => { d.open = false; }));
  const options = document.getElementById('catalogo-estudios');
  const corte = document.getElementById('selector-corte');
  if (corte) {
    const figuras = [...document.querySelectorAll('#cortes-mapa [data-corte]')];
    const seleccionar = () => figuras.forEach(f => f.classList.toggle('plot-hidden', f.dataset.corte !== corte.value));
    corte.addEventListener('change', seleccionar);
    seleccionar();
  }
  const selector = document.getElementById('sens_parametro');
  if (options && selector) selector.addEventListener('change', () => {
    const range = JSON.parse(options.textContent)[selector.value].rango;
    document.getElementById('sens_minimo').value = range[0];
    document.getElementById('sens_maximo').value = range[1];
  });
  document.getElementById('caso')?.addEventListener('invalid', e => {
    activateSection(e.target.closest('.dashboard-panel')?.id || 'simulacion');
    const pane = e.target.closest('.edu-tab-pane');
    if (pane?.hidden) document.getElementById(pane.getAttribute('aria-labelledby'))?.click();
  }, true);
  locationSection();
})();
