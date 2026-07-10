// =============================================================================
// login.js — Hierdie lêer werk saam met die inteken-blad (login.html).
// Dit stuur die gebruiker se e-pos en wagwoord na die bediener en,
// as alles reg is, stuur dit die gebruiker na die tuisblad (home.html).
// =============================================================================

/**
 * login.js — behaviour for login.html only.
 *
 * On submit: sends credentials to POST /token, stores the JWT token
 * and user role in localStorage, then redirects to home.html.
 */

// Hierdie funksie begin dadelik wanneer die inteken-blad oopmaak.
(function () {
  // Vee enige ou inteken-inligting uit sodat die gebruiker weer moet inteken
  // Clear any previous session so the user must log in again
  localStorage.removeItem('isLoggedIn');
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');

  // Hierdie funksie kry die adres van die bediener waarheen ons die data stuur.
  function getApiBaseUrl() {
    // As daar reeds 'n adres gestoor is, gebruik dit
    const stored = localStorage.getItem('apiBaseUrl');
    if (stored) {
      return stored;
    }

    // Anders bou ons die adres uit die blad se eie adres
    const protocol = window.location.protocol || 'http:';
    const host = window.location.hostname || 'localhost';
    return `${protocol}//${host}:8000`;
  }

  const API_BASE_URL = getApiBaseUrl();

  // Kry die inteken-vorm op die blad
  const loginForm = document.getElementById('login-form');

  if (loginForm) {
    // Hierdie funksie loop wanneer die gebruiker die "Teken In" knoppie druk.
    // Dit stuur die e-pos en wagwoord na die bediener om te kyk of dit reg is.
    loginForm.addEventListener('submit', async function (e) {
      // Keer dat die blad self herlaai wanneer die vorm gestuur word
      e.preventDefault();

      // Lees die e-pos en wagwoord wat die gebruiker ingetik het
      const emailInput = document.getElementById('email');
      const passwordInput = document.getElementById('password');
      const email = emailInput.value.trim();
      const password = passwordInput.value;

      // As een van die velde leeg is, wys 'n boodskap en hou op
      if (!email || !password) {
        alert('Vul asseblief beide velde in.');
        return;
      }

      // Skakel die knoppie af terwyl ons besig is, sodat dit nie twee keer gedruk kan word nie
      // Disable button while logging in
      const submitBtn = loginForm.querySelector('button[type="submit"]');
      submitBtn.disabled = true;
      submitBtn.textContent = 'Teken in...';

      try {
        // Maak die data reg om na die bediener te stuur
        // POST /token expects OAuth2 form data (username + password)
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        // Stuur die inteken-inligting na die bediener en wag vir 'n antwoord
        const response = await fetch(API_BASE_URL + '/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData,
        });

        const result = await response.json();

        // As die bediener sê die inteken was suksesvol
        if (response.ok && result.sukses) {
          // Stoor die bewys (token) dat die gebruiker ingeteken is
          // Store the token
          const token = result.data.access_token;
          localStorage.setItem('access_token', token);
          localStorage.setItem('isLoggedIn', 'true');

          // Lees die gebruiker se rol uit die token en stoor dit
          // Decode the JWT payload to get the role
          try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            localStorage.setItem('user_role', payload.rol_naam || '');
          } catch (decodeErr) {
            // As ons nie die rol kan lees nie, stoor 'n leë rol
            localStorage.setItem('user_role', '');
          }

          // Stuur die gebruiker na die tuisblad
          window.location.href = 'home.html';
        } else {
          // Die inteken het misluk: wys die foutboodskap
          alert(result.fout || 'Verkeerde e-pos of wagwoord.');
        }
      } catch (err) {
        // Die bediener kon nie bereik word nie: wys 'n boodskap
        alert('Kon nie aan die bediener koppel nie. Probeer later weer.');
        console.error('[login] Network error:', err);
      } finally {
        // Sit die knoppie terug soos dit was
        submitBtn.disabled = false;
        submitBtn.textContent = 'Teken In';
      }
    });
  }
})();
