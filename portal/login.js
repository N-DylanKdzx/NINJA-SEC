'use strict';

const form = document.querySelector('#login');
const feedback = document.querySelector('#login-feedback');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const submit = form.querySelector('[type=submit]');
  submit.disabled = true;
  feedback.textContent = 'Verificando acceso…';
  try {
    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-NinjaSec-Action': '1'},
      body: JSON.stringify(Object.fromEntries(new FormData(form))),
    });
    if (response.ok) return window.location.replace('/');
    const result = await response.json();
    feedback.textContent = result.error || 'No se pudo iniciar sesión.';
    form.elements.password.focus();
  } catch {
    feedback.textContent = 'No se pudo conectar con el portal. Inténtalo de nuevo.';
  } finally {
    submit.disabled = false;
  }
});
