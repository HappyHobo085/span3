/**
 * login.js — behaviour for login.html only.
 *
 * - Seeds demo data (test user + fake “subscription” for sub_stelsel.html).
 * - Pre-fills email/password so you can click Log in quickly in development.
 * - On submit: compares values to the demo user, then sets isLoggedIn and goes to home.html.
 */

(function () {
  // Clear any previous session so the user must log in again
  localStorage.removeItem('isLoggedIn');

  // ----- Demo credentials (no real server login in this prototype) -----
  const testUser = {
    email: "test@demo.com",
    password: "password123"
  };

  // ----- Fake module row for the Sub Stelsel page dropdown -----
  const testSubDetails = {
    module: "Toegangsbestuur",
    status: "Aktief",
    weergawe: "1.0.4"
  };

  // Persisted for sub_stelsel.html to read on next navigation
  localStorage.setItem('testSubDetails', JSON.stringify(testSubDetails));

  // ----- Optional convenience: fill inputs so testers see the expected values -----
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  if (emailInput && passwordInput) {
    emailInput.value = testUser.email;
    passwordInput.value = testUser.password;
  }

  const loginForm = document.getElementById('login-form');

  if (loginForm) {
    loginForm.addEventListener('submit', function (e) {
      e.preventDefault();

      // --- SPAN-TOETSING: vaste demo-inlog AF — enige stuur stuur deur (aktiveer weer vir produksie) ---
      localStorage.setItem('isLoggedIn', 'true');
      window.location.href = 'home.html';
      // const email = emailInput.value;
      // const password = passwordInput.value;
      // if (email === testUser.email && password === testUser.password) {
      //   localStorage.setItem('isLoggedIn', 'true');
      //   window.location.href = 'home.html';
      // } else {
      //   alert("Invalid credentials. Please use test@demo.com / password123");
      // }
    });
  }
})();
