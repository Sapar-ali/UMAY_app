// UMAY Service Worker - PWA функциональность
const CACHE_VERSION = 'v1.0.3';
const CACHE_NAME = `umay-${CACHE_VERSION}`;
const STATIC_CACHE = `umay-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `umay-dynamic-${CACHE_VERSION}`;

// Файлы для кэширования при установке
// ВНИМАНИЕ: нельзя кэшировать серверные шаблоны по путям /templates/*.html
// Кэшируем только реально доступные по HTTP файлы
const STATIC_FILES = [
  '/',
  // Кэшируем только существующие статические файлы
  '/static/css/style.css',
  '/static/css/mobile.css',
  '/static/js/main.js',
  '/static/js/mobile.js',
  '/static/assets/new-logo.png',
  '/static/assets/umay-pattern.svg',
  '/static/manifest.json'
];

// Установка Service Worker
self.addEventListener('install', (event) => {
  console.log('🔄 UMAY Service Worker: Установка...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('✅ UMAY Service Worker: Статические файлы закэшированы');
        return cache.addAll(STATIC_FILES);
      })
      .catch((error) => {
        console.error('❌ UMAY Service Worker: Ошибка кэширования:', error);
      })
  );
  
  self.skipWaiting();
});

// Активация Service Worker
self.addEventListener('activate', (event) => {
  console.log('🚀 UMAY Service Worker: Активация...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('🗑️ UMAY Service Worker: Удаление старого кэша:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('✅ UMAY Service Worker: Активирован и готов к работе');
        return self.clients.claim();
      })
  );
});

// Перехват сетевых запросов
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Пропускаем не-GET запросы
  if (request.method !== 'GET') {
    return;
  }
  
  // Пропускаем внешние запросы
  if (url.origin !== location.origin) {
    return;
  }
  
  // Стратегия кэширования: Cache First для статики, Network First для HTML/API
  if (isStaticFile(request.url)) {
    event.respondWith(cacheFirst(request));
  } else {
    event.respondWith(networkFirst(request));
  }
});

// Стратегия Cache First для статических файлов
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('❌ UMAY Service Worker: Ошибка сети:', error);
    return new Response('Offline - проверьте подключение к интернету', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'text/plain' }
    });
  }
}

// Стратегия Network First для динамических страниц
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('📱 UMAY Service Worker: Используем кэш для:', request.url);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Fallback для HTML страниц
    if (request.headers.get('accept') && request.headers.get('accept').includes('text/html')) {
      // Возвращаем базовую заглушку HTML, чтобы избежать белого экрана
      return new Response(`<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>UMAY</title></head><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 24px;"><h1>UMAY</h1><p>Нет сети. Попробуйте еще раз, когда подключение восстановится.</p><p><a href="/">На главную</a></p></body></html>`, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
    }
    
    return new Response('Offline - проверьте подключение к интернету', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'text/plain' }
    });
  }
}

// Проверка, является ли файл статическим
function isStaticFile(url) {
  const staticExtensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.webp'];
  return staticExtensions.some(ext => url.includes(ext));
}

// Push уведомления
self.addEventListener('push', (event) => {
  console.log('📱 UMAY Service Worker: Получено push уведомление');
  
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body || 'UMAY - новое уведомление',
      icon: '/static/assets/new-logo.png',
      badge: '/static/assets/new-logo.png',
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: 1
      },
      actions: [
        {
          action: 'explore',
          title: 'Открыть',
          icon: '/static/assets/new-logo.png'
        },
        {
          action: 'close',
          title: 'Закрыть',
          icon: '/static/assets/new-logo.png'
        }
      ]
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title || 'UMAY', options)
    );
  }
});

// Обработка кликов по уведомлениям
self.addEventListener('notificationclick', (event) => {
  console.log('👆 UMAY Service Worker: Клик по уведомлению');
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Обработка ошибок
self.addEventListener('error', (event) => {
  console.error('❌ UMAY Service Worker: Ошибка:', event.error);
});

self.addEventListener('unhandledrejection', (event) => {
  console.error('❌ UMAY Service Worker: Необработанная ошибка:', event.reason);
});

console.log('🚀 UMAY Service Worker загружен и готов к работе!');
