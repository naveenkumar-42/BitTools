document.getElementById('openTranslator').addEventListener('click', () => {
    chrome.tabs.create({ url: 'https://tamiltranslator.pythonanywhere.com/' });
  });
  