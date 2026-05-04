//front end javascript kode wat die API calls en data van die backend python kode roep

//Ek persoonlik dink ons moet 'n javascript file skep vir elke web bladsy, dit gaan dit meer effektief maak en makliker maak

(function() {
    // Check if user is logged in
    const isLoggedIn = localStorage.getItem('isLoggedIn');
    const currentPage = window.location.pathname.split('/').pop();

    if (!isLoggedIn && currentPage !== 'login.html') {
        window.location.href = 'login.html';
    }
})();
