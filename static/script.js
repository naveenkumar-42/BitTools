function toggleMenu() {
  document.querySelector('.menu-links').classList.toggle('active');
}

// Close menu when clicking outside (for mobile only)
document.addEventListener('click', function (event) {
  const menu = document.querySelector('.menu-links');
  const menuIcon = document.querySelector('.menu-icon');

  if (!menu.contains(event.target) && !menuIcon.contains(event.target)) {
    menu.classList.remove('active');
  }
});

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('pdf_file');
const fileNameDisplay = document.getElementById('file-name');

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) {
    fileNameDisplay.textContent = `Selected File: ${fileInput.files[0].name}`;
  }
});

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) {
    fileInput.files = e.dataTransfer.files;
    fileNameDisplay.textContent = `Selected File: ${fileInput.files[0].name}`;
  }
});