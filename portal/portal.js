'use strict';

const form = document.querySelector('#incident');
const feedback = document.querySelector('#feedback');
const incidents = document.querySelector('#incidents');
const editorTitle = document.querySelector('#editor-title');
const logout = document.querySelector('#logout');
const statuses = {abierto: 'Abierto', en_progreso: 'En progreso', resuelto: 'Resuelto'};
let editing = null;

async function api(path, method = 'GET', data) {
  const headers = {'X-NinjaSec-Action': '1'};
  if (data) headers['Content-Type'] = 'application/json';
  const response = await fetch(`/api/incidents${path}`, {method, headers, body: data && JSON.stringify(data)});
  if (response.status === 401) {
    window.location.replace('/');
    throw new Error('La sesión ha caducado.');
  }
  if (response.status === 204) return;
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Error ${response.status}`);
  return result;
}

function button(label, action) {
  const control = document.createElement('button');
  control.textContent = label;
  control.addEventListener('click', action);
  return control;
}

async function refresh() {
  const items = await api('');
  incidents.replaceChildren(...items.map((item) => {
    const row = document.createElement('li');
    const title = document.createElement('strong');
    title.textContent = `#${item.id} ${item.title} · ${statuses[item.status]}`;
    const description = document.createElement('p');
    description.textContent = item.description;
    const actions = document.createElement('div');
    actions.className = 'actions';
    actions.append(button('Editar', () => {
      editing = item.id;
      editorTitle.textContent = `Editar incidente #${item.id}`;
      for (const key of ['title', 'description', 'status']) form.elements[key].value = item[key];
      form.elements.title.focus();
      feedback.textContent = `Editando incidente #${item.id}.`;
    }), button('Eliminar', async () => {
      if (!window.confirm(`¿Eliminar el incidente #${item.id}?`)) return;
      try {
        await api(`/${item.id}`, 'DELETE');
        if (editing === item.id) form.reset();
        feedback.textContent = 'Incidente eliminado.';
        await refresh();
      } catch (error) { feedback.textContent = error.message; }
    }));
    row.append(title, description, actions);
    return row;
  }));
  if (!items.length) {
    const empty = document.createElement('li');
    empty.textContent = 'Todavía no hay incidentes registrados.';
    incidents.append(empty);
  }
}

form.addEventListener('reset', () => {
  editing = null;
  editorTitle.textContent = 'Nuevo incidente';
});
logout.addEventListener('click', async () => {
  logout.disabled = true;
  try {
    const response = await fetch('/auth/logout', {method: 'POST', headers: {'X-NinjaSec-Action': '1'}});
    if (!response.ok) throw new Error();
    window.location.replace('/');
  } catch {
    feedback.textContent = 'No se pudo cerrar la sesión. Inténtalo de nuevo.';
    logout.disabled = false;
  }
});
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const submit = form.querySelector('[type=submit]');
  submit.disabled = true;
  try {
    await api(editing ? `/${editing}` : '', editing ? 'PUT' : 'POST', Object.fromEntries(new FormData(form)));
    form.reset();
    feedback.textContent = 'Incidente guardado.';
    await refresh();
  } catch (error) { feedback.textContent = error.message; }
  finally { submit.disabled = false; }
});
refresh().catch((error) => { feedback.textContent = error.message; });
