// UMAY Mobile PWA JavaScript
class UMAYPWA {
  constructor() {
    this.isInstalled = false;
    this.deferredPrompt = null;
    this.isOnline = navigator.onLine;
    
    this.init();
  }
  
  async init() {
    console.log('🚀 UMAY PWA: Инициализация...');
    
    // Регистрация Service Worker
    await this.registerServiceWorker();
    
    // Инициализация PWA
    await this.initPWA();
    
    // Настройка событий
    this.setupEventListeners();
    
    // Настроить кнопку установки для iOS/Android
    this.setupInstallCTA();
    
    // Проверка установки
    this.checkInstallation();
    
    console.log('✅ UMAY PWA: Инициализация завершена');
  }
  
  // Регистрация Service Worker
  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        // Регистрируем SW на корне, чтобы охватывал все страницы
        const registration = await navigator.serviceWorker.register('/sw.js');
        console.log('✅ UMAY PWA: Service Worker зарегистрирован:', registration);
        
        // Обработка обновлений
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.showUpdateNotification();
            }
          });
        });
        
      } catch (error) {
        console.error('❌ UMAY PWA: Ошибка регистрации Service Worker:', error);
      }
    } else {
      console.warn('⚠️ UMAY PWA: Service Worker не поддерживается');
    }
  }
  
  // Инициализация PWA
  async initPWA() {
    // Проверка поддержки PWA
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      console.warn('⚠️ UMAY PWA: PWA не поддерживается');
      return;
    }
    
    // Запрос разрешений на уведомления
    if ('Notification' in window && Notification.permission === 'default') {
      this.requestNotificationPermission();
    }
    
    // Проверка online/offline статуса
    this.updateOnlineStatus();
  }
  
  // Настройка событий
  setupEventListeners() {
    // Событие установки PWA
    window.addEventListener('beforeinstallprompt', (e) => {
      console.log('📱 UMAY PWA: Доступна установка');
      e.preventDefault();
      this.deferredPrompt = e;
      this.showInstallPrompt();
    });
    
    // Событие успешной установки
    window.addEventListener('appinstalled', () => {
      console.log('✅ UMAY PWA: Приложение установлено');
      this.isInstalled = true;
      this.hideInstallPrompt();
      this.showSuccessMessage('UMAY успешно установлен на ваш телефон!');
    });
    
    // Online/offline события
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.updateOnlineStatus();
      this.showSuccessMessage('Подключение к интернету восстановлено');
    });
    
    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.updateOnlineStatus();
      this.showWarningMessage('Нет подключения к интернету. Работаем в offline режиме');
    });
    
    // Touch события для мобильных жестов
    this.setupTouchGestures();
    
    // Swipe события
    this.setupSwipeGestures();
  }

  // Показать кнопку установки и поведение для разных платформ
  setupInstallCTA() {
    const baseInstallBtn = document.getElementById('install-pwa-btn');
    const pageInstallBtn = document.getElementById('mobile-install-btn');

    const isInStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isChromeIOS = /CriOS/.test(navigator.userAgent);

    // Если уже установлено — ничего не показываем
    if (isInStandalone) {
      if (baseInstallBtn) baseInstallBtn.classList.add('hidden');
      return;
    }

    // Android: кнопку показываем при beforeinstallprompt (обработано в showInstallPrompt)
    // iOS: собственного промпта нет — показываем кнопку, по клику даём нативную инструкцию
    if (isIOS) {
      if (baseInstallBtn) {
        baseInstallBtn.classList.remove('hidden');
        baseInstallBtn.addEventListener('click', () => this.showiOSInstallHelp(isChromeIOS));
      }
      if (pageInstallBtn) {
        pageInstallBtn.addEventListener('click', () => this.showiOSInstallHelp(isChromeIOS));
      }
    }
  }
  
  // Настройка touch жестов
  setupTouchGestures() {
    let startX = 0;
    let startY = 0;
    let startTime = 0;
    
    document.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      startTime = Date.now();
    });
    
    document.addEventListener('touchend', (e) => {
      const endX = e.changedTouches[0].clientX;
      const endY = e.changedTouches[0].clientY;
      const endTime = Date.now();
      
      const deltaX = endX - startX;
      const deltaY = endY - startY;
      const deltaTime = endTime - startTime;
      
      // Определение типа жеста
      if (deltaTime < 300 && Math.abs(deltaX) > 50 && Math.abs(deltaY) < 100) {
        if (deltaX > 0) {
          this.handleSwipeRight();
        } else {
          this.handleSwipeLeft();
        }
      }
      
      // Tap gesture
      if (deltaTime < 200 && Math.abs(deltaX) < 10 && Math.abs(deltaY) < 10) {
        this.handleTap();
      }
    });
  }
  
  // Настройка swipe жестов
  setupSwipeGestures() {
    let startX = 0;
    let startY = 0;
    
    document.addEventListener('mousedown', (e) => {
      startX = e.clientX;
      startY = e.clientY;
    });
    
    document.addEventListener('mouseup', (e) => {
      const deltaX = e.clientX - startX;
      const deltaY = e.clientY - startY;
      
      if (Math.abs(deltaX) > 50 && Math.abs(deltaY) < 100) {
        if (deltaX > 0) {
          this.handleSwipeRight();
        } else {
          this.handleSwipeLeft();
        }
      }
    });
  }
  
  // Обработка жестов
  handleSwipeRight() {
    console.log('👉 UMAY PWA: Swipe вправо');
    // Можно использовать для навигации назад
    if (window.history.length > 1) {
      window.history.back();
    }
  }
  
  handleSwipeLeft() {
    console.log('👈 UMAY PWA: Swipe влево');
    // Можно использовать для навигации вперед
    if (window.history.length > 1) {
      window.history.forward();
    }
  }
  
  handleTap() {
    console.log('👆 UMAY PWA: Tap gesture');
    // Можно использовать для специальных действий
  }
  
  // Показать prompt для установки
  showInstallPrompt() {
    if (this.deferredPrompt) {
      const installButton = document.getElementById('install-pwa-btn');
      if (installButton) {
        installButton.classList.remove('hidden');
        installButton.addEventListener('click', () => {
          this.installPWA();
        });
      }
    }
  }
  
  // Скрыть prompt для установки
  hideInstallPrompt() {
    const installButton = document.getElementById('install-pwa-btn');
    if (installButton) {
      installButton.style.display = 'none';
    }
  }
  
  // Установка PWA
  async installPWA() {
    if (this.deferredPrompt) {
      this.deferredPrompt.prompt();
      const { outcome } = await this.deferredPrompt.userChoice;
      
      if (outcome === 'accepted') {
        console.log('✅ UMAY PWA: Пользователь согласился на установку');
      } else {
        console.log('❌ UMAY PWA: Пользователь отказался от установки');
      }
      
      this.deferredPrompt = null;
    }
  }

  // Подсказка для установки на iOS
  showiOSInstallHelp(isChromeIOS = false) {
    // Показать компактное понятное объяснение вместо большого баннера
    if (isChromeIOS) {
      this.showWarningMessage('Установка iOS возможна только через Safari. Откройте сайт в Safari.');
      return;
    }
    this.showWarningMessage('Safari → Поделиться → На экран «Домой». Это ограничение iOS для всех PWA.');
  }
  
  // Запрос разрешения на уведомления
  async requestNotificationPermission() {
    try {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        console.log('✅ UMAY PWA: Разрешение на уведомления получено');
        this.subscribeToPushNotifications();
      } else {
        console.log('❌ UMAY PWA: Разрешение на уведомления отклонено');
      }
    } catch (error) {
      console.error('❌ UMAY PWA: Ошибка запроса разрешений:', error);
    }
  }
  
  // Подписка на push уведомления
  async subscribeToPushNotifications() {
    if ('serviceWorker' in navigator && 'PushManager' in window) {
      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: this.urlBase64ToUint8Array('YOUR_VAPID_PUBLIC_KEY')
        });
        
        console.log('✅ UMAY PWA: Подписка на push уведомления создана');
        
        // Отправка подписки на сервер
        this.sendSubscriptionToServer(subscription);
        
      } catch (error) {
        console.error('❌ UMAY PWA: Ошибка подписки на push:', error);
      }
    }
  }
  
  // Отправка подписки на сервер
  async sendSubscriptionToServer(subscription) {
    try {
      const response = await fetch('/api/push-subscription', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscription)
      });
      
      if (response.ok) {
        console.log('✅ UMAY PWA: Подписка отправлена на сервер');
      }
    } catch (error) {
      console.error('❌ UMAY PWA: Ошибка отправки подписки:', error);
    }
  }
  
  // Конвертация VAPID ключа
  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }
  
  // Проверка установки
  checkInstallation() {
    if (window.matchMedia('(display-mode: standalone)').matches || 
        window.navigator.standalone === true) {
      this.isInstalled = true;
      console.log('✅ UMAY PWA: Приложение запущено в standalone режиме');
    }
  }
  
  // Обновление online статуса
  updateOnlineStatus() {
    const statusElement = document.getElementById('online-status');
    if (statusElement) {
      if (this.isOnline) {
        statusElement.textContent = '🟢 Онлайн';
        statusElement.className = 'text-green-600';
      } else {
        statusElement.textContent = '🔴 Офлайн';
        statusElement.className = 'text-red-600';
      }
    }
  }
  
  // Показать уведомление об обновлении
  showUpdateNotification() {
    if (confirm('Доступна новая версия UMAY. Обновить сейчас?')) {
      window.location.reload();
    }
  }
  
  // Показать сообщение об успехе
  showSuccessMessage(message) {
    this.showToast(message, 'success');
  }
  
  // Показать предупреждение
  showWarningMessage(message) {
    this.showToast(message, 'warning');
  }
  
  // Показать toast сообщение
  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
      type === 'success' ? 'bg-green-500 text-white' :
      type === 'warning' ? 'bg-yellow-500 text-white' :
      'bg-blue-500 text-white'
    }`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.remove();
    }, 3000);
  }
  
  // Получить информацию о PWA
  getPWAInfo() {
    return {
      isInstalled: this.isInstalled,
      isOnline: this.isOnline,
      supportsPWA: 'serviceWorker' in navigator && 'PushManager' in window,
      notificationPermission: Notification.permission
    };
  }
}

// Инициализация PWA при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
  window.umayPWA = new UMAYPWA();
});

// Экспорт для использования в других модулях
if (typeof module !== 'undefined' && module.exports) {
  module.exports = UMAYPWA;
}
