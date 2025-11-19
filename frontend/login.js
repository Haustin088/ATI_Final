// DOM elements
const loginForm = document.getElementById('loginForm');
const forgotPasswordForm = document.getElementById('forgotPasswordForm');
const loginFormElement = document.getElementById('loginFormElement');
const resetFormElement = document.getElementById('resetFormElement');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');
const togglePassword = document.getElementById('togglePassword');
const passwordInput = document.getElementById('password');
const eyeIcon = document.getElementById('eyeIcon');
const loginBtn = document.getElementById('loginBtn');
const loginBtnText = document.getElementById('loginBtnText');
const loginSpinner = document.getElementById('loginSpinner');
const adminRoleBtn = document.getElementById('adminRoleBtn');
const editorRoleBtn = document.getElementById('editorRoleBtn');

let selectedRole = 'admin';
adminRoleBtn.classList.add('active');

// 🧠 Role switch
adminRoleBtn.addEventListener('click', () => {
  selectedRole = 'admin';
  adminRoleBtn.classList.add('active');
  editorRoleBtn.classList.remove('active');
  hideMessages();
});

editorRoleBtn.addEventListener('click', () => {
  selectedRole = 'editor';
  editorRoleBtn.classList.add('active');
  adminRoleBtn.classList.remove('active');
  hideMessages();
});

// 👁 Password visibility toggle
togglePassword.addEventListener('click', () => {
  const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
  passwordInput.setAttribute('type', type);
  eyeIcon.innerHTML =
    type === 'text'
      ? `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"></path>`
      : `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
         <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>`;
});

// ✉️ Message helpers
function showError(message) {
  document.getElementById('errorText').textContent = message;
  errorMessage.classList.remove('hidden');
  successMessage.classList.add('hidden');
}
function showSuccess(message) {
  document.getElementById('successText').textContent = message;
  successMessage.classList.remove('hidden');
  errorMessage.classList.add('hidden');
}
function hideMessages() {
  errorMessage.classList.add('hidden');
  successMessage.classList.add('hidden');
}
function showLoading() {
  loginBtnText.textContent = 'Đang xử lý...';
  loginSpinner.classList.remove('hidden');
  loginBtn.disabled = true;
}
function hideLoading() {
  loginBtnText.textContent = 'Đăng Nhập';
  loginSpinner.classList.add('hidden');
  loginBtn.disabled = false;
}

// 🚀 Redirect
function redirectToDashboard(user) {
  const dashboardUrl = user.role === 'admin' ? 'Admin.html' : 'Editor.html';
  setTimeout(() => (window.location.href = dashboardUrl), 1500);
}

// 🔐 Handle login submission
loginFormElement.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideMessages();

  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;

  if (!username || !password) {
    showError('Vui lòng nhập đầy đủ thông tin!');
    return;
  }

  showLoading();

  try {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const res = await fetch('http://localhost:8000/login', {
      method: 'POST',
      body: formData,
    });

    hideLoading();

    if (!res.ok) {
      showError('Tên đăng nhập hoặc mật khẩu không đúng!');
      return;
    }

    const user = await res.json();

    if (user.role !== selectedRole) {
      showError(`Tài khoản này không có quyền truy cập với vai trò ${selectedRole === 'admin' ? 'Admin' : 'Editor'}!`);
      return;
    }

    showSuccess(`Đăng nhập thành công! Chào mừng ${user.name}`);
    redirectToDashboard(user);
  } catch (err) {
    hideLoading();
    showError('Không thể kết nối tới máy chủ!');
  }
});

// 📨 Forgot password (UI only)
document.getElementById('forgotPasswordBtn').addEventListener('click', () => {
  loginForm.classList.add('hidden');
  forgotPasswordForm.classList.remove('hidden');
});
document.getElementById('backToLoginBtn').addEventListener('click', () => {
  forgotPasswordForm.classList.add('hidden');
  loginForm.classList.remove('hidden');
  hideMessages();
});
resetFormElement.addEventListener('submit', (e) => {
  e.preventDefault();
  setTimeout(() => {
    document.getElementById('resetMessage').classList.remove('hidden');
    resetFormElement.reset();
  }, 1000);
});
