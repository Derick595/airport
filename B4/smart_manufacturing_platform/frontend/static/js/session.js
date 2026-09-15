const SessionUI = {
  nameKey: "aero_mes_session_name",
  themeKey: "aero_mes_theme",

  init() {
    this.applyTheme(localStorage.getItem(this.themeKey) === "light" ? "light" : "dark");
    document.getElementById("login-form").addEventListener("submit", event => this.login(event));
    document.getElementById("logout-button").addEventListener("click", () => this.logout());
    document.getElementById("login-theme-toggle").addEventListener("click", () => this.toggleTheme());
    document.getElementById("app-theme-toggle").addEventListener("click", () => this.toggleTheme());

    const name = sessionStorage.getItem(this.nameKey);
    if (name) {
      this.showDashboard(name);
      App.init();
    } else {
      this.showLogin();
    }
  },

  login(event) {
    event.preventDefault();
    const input = document.getElementById("login-name");
    const name = input.value.trim().replace(/\s+/g, " ");
    const error = document.getElementById("login-error");
    if (!name) {
      error.hidden = false;
      input.focus();
      return;
    }
    error.hidden = true;
    sessionStorage.setItem(this.nameKey, name);
    window.location.reload();
  },

  logout() {
    sessionStorage.removeItem(this.nameKey);
    window.location.reload();
  },

  showLogin() {
    document.getElementById("app-shell").hidden = true;
    document.getElementById("login-screen").hidden = false;
    document.getElementById("login-name").focus();
  },

  showDashboard(name) {
    document.getElementById("session-name").textContent = name;
    document.getElementById("login-screen").hidden = true;
    document.getElementById("app-shell").hidden = false;
  },

  toggleTheme() {
    const theme = document.body.dataset.theme === "light" ? "dark" : "light";
    localStorage.setItem(this.themeKey, theme);
    this.applyTheme(theme);
  },

  applyTheme(theme) {
    document.body.dataset.theme = theme;
    if (window.SPCChart) SPCChart.updateTheme();
    const next = theme === "light" ? "dark" : "light";
    for (const id of ["login-theme-toggle", "app-theme-toggle"]) {
      const button = document.getElementById(id);
      button.setAttribute("aria-label", `Switch to ${next} mode`);
      button.querySelector("i").className = next === "light" ? "fa-solid fa-sun" : "fa-solid fa-moon";
      button.querySelector("span").textContent = id === "app-theme-toggle" ? (next === "light" ? "Light" : "Dark") : `${next[0].toUpperCase()}${next.slice(1)} mode`;
    }
  }
};

window.SessionUI = SessionUI;
