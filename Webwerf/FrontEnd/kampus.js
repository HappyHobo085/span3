// Kampus-bladsy: soekfilter, modal, en stuur nuwe klas-data na main.js (MoonApi) -> backend.

(function () {
  const listSearch = document.getElementById('list-search');
  const dataList = document.getElementById('data-list');
  const openClassModalButton = document.getElementById('open-class-modal');
  const closeClassModalButton = document.getElementById('close-class-modal');
  const createClassButton = document.getElementById('create-class-button');
  const classModalOverlay = document.getElementById('class-modal-overlay');
  const classRoomName = document.getElementById('class-room-name');
  const classDescription = document.getElementById('class-description');
  const classNfcTag = document.getElementById('class-nfc-tag');
  const dataSelect = document.getElementById('data-select');

  function applyListFilter() {
    if (!listSearch || !dataList) return;
    const query = listSearch.value.trim().toLowerCase();
    const items = dataList.querySelectorAll('li');

    items.forEach(function (li) {
      const text = (li.textContent || '').trim().toLowerCase();
      const matches = query === '' || text.includes(query);
      li.hidden = !matches;
    });
  }

  function openClassModal() {
    if (!classModalOverlay) return;
    classModalOverlay.classList.add('open');
    classModalOverlay.setAttribute('aria-hidden', 'false');
  }

  function closeClassModal() {
    if (!classModalOverlay) return;
    classModalOverlay.classList.remove('open');
    classModalOverlay.setAttribute('aria-hidden', 'true');
  }

  /**
   * Laai kampusse vanaf API en vul die dropdown (IDs uit databasis).
   */
  async function loadKampusDropdown() {
    if (!dataSelect || !window.MoonApi) return;
    try {
      const json = await window.MoonApi.fetchKampusse();
      if (json && json.sukses && Array.isArray(json.data) && json.data.length > 0) {
        dataSelect.innerHTML = '';
        json.data.forEach(function (k) {
          const opt = document.createElement('option');
          opt.value = String(k.Kampus_ID);
          opt.textContent = k.KAM_Naam;
          dataSelect.appendChild(opt);
        });
      }
    } catch (e) {
      console.warn('Kon nie kampuslys laai nie:', e);
    }
  }

  /**
   * Neem vormdata en roep MoonApi.createKlas (main.js) aan wat na main.py POST /klasse gaan.
   */
  async function submitNewClass() {
    const roomName = classRoomName ? classRoomName.value.trim() : '';
    const description = classDescription ? classDescription.value.trim() : '';
    const nfcTag = classNfcTag ? classNfcTag.value.trim() : '';

    if (!roomName || !description || !nfcTag) {
      alert('Voltooi asseblief al die velde.');
      return;
    }

    if (!window.MoonApi || typeof window.MoonApi.createKlas !== 'function') {
      alert('API is nie beskikbaar nie. Laai main.js voor kampus.js.');
      return;
    }

    const kampusId = dataSelect ? dataSelect.value : null;

    try {
      const json = await window.MoonApi.createKlas({
        naam: roomName,
        beskrywing: description,
        nfc_uid: nfcTag,
        kampus_id: kampusId,
      });

      if (json && json.sukses) {
        alert('Klas suksesvol gestoor in die databasis.');
        closeClassModal();
        if (classRoomName) classRoomName.value = '';
        if (classDescription) classDescription.value = '';
        if (classNfcTag) classNfcTag.value = '';
        return;
      }

      const fout =
        (json && json.fout) ||
        'Kon nie klas skep nie. Gaan na login-token (access_token) en backend.';
      alert(fout);
    } catch (err) {
      console.error(err);
      alert(
        'Netwerkfout: maak seker die backend loop en CORS is aan (' +
          (window.MoonApi && window.MoonApi.baseUrl) +
          ').'
      );
    }
  }

  if (listSearch) {
    listSearch.addEventListener('input', applyListFilter);
  }

  if (openClassModalButton) {
    openClassModalButton.addEventListener('click', openClassModal);
  }

  if (closeClassModalButton) {
    closeClassModalButton.addEventListener('click', closeClassModal);
  }

  if (classModalOverlay) {
    classModalOverlay.addEventListener('click', function (event) {
      if (event.target === classModalOverlay) {
        closeClassModal();
      }
    });
  }

  if (createClassButton) {
    createClassButton.addEventListener('click', function () {
      submitNewClass();
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadKampusDropdown();
  });
})();
