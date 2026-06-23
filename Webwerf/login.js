/**
 * login.js — behaviour for login.html only.
 *
 * On submit: sends credentials to POST /token, stores the JWT token
 * and user role in localStorage, then redirects to home.html.
 */

(function () {
  // Clear any previous session so the user must log in again
  localStorage.removeItem('isLoggedIn');
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');

  const API_BASE_URL = 'http://happyhobo-pc.tail251156.ts.net:8000';

  const loginForm = document.getElementById('login-form');

  if (loginForm) {
    loginForm.addEventListener('submit', async function (e) {
      e.preventDefault();

      const emailInput = document.getElementById('email');
      const passwordInput = document.getElementById('password');
      const email = emailInput.value.trim();
      const password = passwordInput.value;

      if (!email || !password) {
        alert('Vul asseblief beide velde in.');
        return;
      }

      // Disable button while logging in
      const submitBtn = loginForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Teken in...';

      try {
        // POST /token expects OAuth2 form data (username + password)
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await fetch(API_BASE_URL + '/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData,
        });

        const result = await response.json();

        if (response.ok && result.sukses) {
          // Store the token
          const token = result.data.access_token;
          localStorage.setItem('access_token', token);
          localStorage.setItem('isLoggedIn', 'true');

          // Decode the JWT payload to get the role
          try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            localStorage.setItem('user_role', payload.rol_naam || '');
          } catch (decodeErr) {
            localStorage.setItem('user_role', '');
          }

          window.location.href = 'home.html';
        } else {
          alert(result.fout || 'Verkeerde e-pos of wagwoord.');
        }
      } catch (err) {
        alert('Kon nie aan die bediener koppel nie. Probeer later weer.');
        console.error('[login] Network error:', err);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Teken In';
      }
    });
  }
})();
