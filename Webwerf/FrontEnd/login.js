(function () {
  // Test User Details (Task 7)
  const testUser = {
    email: "test@demo.com",
    password: "password123"
  };

  // Test Sub Details for sub_stelsel page (Task 7)
  const testSubDetails = {
    module: "Toegangsbestuur",
    status: "Aktief",
    weergawe: "1.0.4"
  };

  // Store test data so it can be used on other pages
  localStorage.setItem('testSubDetails', JSON.stringify(testSubDetails));

  // Auto-fill for demo purposes (optional but helpful)
  const emailInput = document.getElementById('email');
  const passwordInput = document.getElementById('password');
  if (emailInput && passwordInput) {
    emailInput.value = testUser.email;
    passwordInput.value = testUser.password;
  }

  // Get login form element
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
