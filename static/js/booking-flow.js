// booking-flow.js - مدیریت خروج از فرآیند رزرو

// تابع کمکی برای تشخیص کلیک روی dropdown-toggle
function isDropdownToggleClick(e) {
    const btn = e.currentTarget;
    return btn.hasAttribute('data-bs-toggle') && 
           btn.getAttribute('data-bs-toggle') === 'dropdown' &&
           (btn.classList.contains('show') || 
            btn.getAttribute('aria-expanded') === 'true');
}

class BookingExitGuard {
    constructor() {
        this.popupShown = false;
        this.exitTargetUrl = null;
        this.allowBrowserUnload = false;
        this.bookingPages = [
            '/reserve',
            '/select-date',
            '/contact-info',
            '/payment-confirm'
        ];
        this.isBookingPage = this.bookingPages.some(page => 
            window.location.pathname.includes(page)
        );
        
        if (this.isBookingPage) {
            this.init();
        }
        
    }

    init() {
        this.createModal();
        this.attachLinkListeners();
        this.attachFormListeners();
        this.attachBackButtonListener();
    }

    createModal() {
        if (document.getElementById('exit-confirmation-modal')) return;

        const modal = document.createElement('div');
        modal.id = 'exit-confirmation-modal';
        modal.style.cssText = `
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.6);
            backdrop-filter: blur(3px);
            justify-content: center;
            align-items: center;
            z-index: 99999;
        `;

        modal.innerHTML = `
            <div class="modal-content">
                <button id="close-exit-modal" type="button">
                    <i class="fas fa-times"></i>
                </button>
                
                <div class="modal-warning-icon">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                
                <h4 class="modal-title">آیا مطمئن هستید؟</h4>
                
                <p class="modal-text">
                    در صورت خروج، اطلاعات رزرو فعلی شما از بین خواهد رفت 
                    و باید از ابتدا شروع کنید.
                </p>
                
                <div class="modal-buttons">
                    <button id="btn-stay" class="btn-stay">
                        <i class="fas fa-check-circle me-2"></i>
                        ادامه رزرو
                    </button>
                    <button id="btn-exit" class="btn-exit">
                        <i class="fas fa-sign-out-alt me-2"></i>
                        خروج از رزرو
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.setupModalButtons();
    }
    setupModalButtons() {
        document.getElementById('close-exit-modal').onclick = () => this.closeModal();
        document.getElementById('btn-stay').onclick = () => this.closeModal();
        document.getElementById('btn-exit').onclick = () => this.confirmExit();
    }

    closeModal() {
        document.getElementById('exit-confirmation-modal').style.display = 'none';
        this.popupShown = false;
    }

    confirmExit() {
        // ارسال درخواست به سرور برای پاک کردن سشن
        fetch('/booking/exit-flow/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken(),
                'Content-Type': 'application/json'
            }
        }).finally(() => {
            if (this.exitTargetUrl) {
                window.location.href = this.exitTargetUrl;
            } else {
                window.location.href = '/';
            }
        });
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
    }

    attachLinkListeners() {
        // 1. برای همه لینک‌های <a>
        document.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', (e) => {
                if (this.shouldAllowNavigation(link)) {
                    this.allowBrowserUnload = true; // 👈 اضافه شود
                    return;
                }

                
                e.preventDefault();
                this.exitTargetUrl = link.href;
                this.showModal();
            });
        });
        
        // 2. برای دکمه اعلان (notification-bell)
        const notificationBell = document.getElementById('notification-bell');
        if (notificationBell) {
            notificationBell.addEventListener('click', (e) => {
                // فقط وقتی که واقعاً می‌خواهد به صفحه اعلانات برود
                // (نه وقتی که می‌خواهد dropdown را باز کند)
                const isOpeningDropdown = e.currentTarget.classList.contains('show') || 
                                        e.currentTarget.getAttribute('aria-expanded') === 'true';
                
                if (isOpeningDropdown) {
                    return; // dropdown در حال باز شدن است
                }
                
                if (this.shouldAllowNavigation(notificationBell)) {
                    this.allowBrowserUnload = true;
                    return;
                }
                
                e.preventDefault();
                e.stopPropagation();
                this.exitTargetUrl = notificationBell.getAttribute('data-url');
                this.showModal();
            });
        }
        
        // 3. برای دکمه پروفایل
        document.querySelectorAll('.header-user[data-url]').forEach(profileBtn => {
            profileBtn.addEventListener('click', (e) => {
                const isOpeningDropdown = e.currentTarget.classList.contains('show') || 
                                        e.currentTarget.getAttribute('aria-expanded') === 'true';
                
                if (isOpeningDropdown) {
                    return;
                }
                
                if (this.shouldAllowNavigation(profileBtn)) {
                    this.allowBrowserUnload = true;
                    return;
                }
                
                e.preventDefault();
                e.stopPropagation();
                this.exitTargetUrl = profileBtn.getAttribute('data-url');
                this.showModal();
            });
        });
        
        // 4. برای آیتم‌های داخل dropdown منوی پروفایل
        document.querySelectorAll('.dropdown-menu a').forEach(dropdownItem => {
            dropdownItem.addEventListener('click', (e) => {
                if (this.shouldAllowNavigation(dropdownItem)) {
                    this.allowBrowserUnload = true;
                    return;
                }
                
                e.preventDefault();
                this.exitTargetUrl = dropdownItem.getAttribute('href');
                this.showModal();
            });
        });
    }

    attachFormListeners() {
        // اجازه دادن به سابمیت فرم‌ها بدون پاپ‌آپ
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', () => {
                this.popupShown = true; // غیرفعال کردن پاپ‌آپ برای فرم
            });
        });
    }

    attachBackButtonListener() {
        window.addEventListener('beforeunload', (e) => {
            if (!this.popupShown && !this.allowBrowserUnload) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }


    shouldAllowNavigation(element) {
        // ✅ اگر عنصر دکمه خاص رزرو است (مثل انتخاب سرویس)
        if (element.hasAttribute('data-no-exit') || 
            element.classList.contains('booking-exit-link')) {
            return true;
        }
        
        // ✅ اگر داخل فرم است
        if (element.closest('form')) {
            return true;
        }
        
        // ✅ اگر anchor داخلی است
        if (element.getAttribute('href') && element.getAttribute('href').startsWith('#')) {
            return true;
        }
        
        // ✅ دریافت مسیر مقصد
        let targetUrl = null;
        
        // برای <a> تگ‌ها
        if (element.tagName === 'A') {
            targetUrl = element.getAttribute('href');
        }
        // برای دکمه‌هایی که data-url دارند (اعلان و پروفایل)
        else if (element.hasAttribute('data-url')) {
            targetUrl = element.getAttribute('data-url');
        }
        // برای دکمه‌هایی که href دارند (بعضی از دکمه‌ها)
        else if (element.hasAttribute('href')) {
            targetUrl = element.getAttribute('href');
        }
        
        // اگر هیچ URLی ندارد، اجازه بده
        if (!targetUrl || targetUrl.trim() === '') {
            return true;
        }
        
        // ✅ مسیر کنونی و مقصد
        const currentPath = window.location.pathname;
        let targetPath = '';
        
        try {
            targetPath = new URL(targetUrl, window.location.origin).pathname;
        } catch {
            targetPath = targetUrl;
        }
        
        // ✅ اگر همان صفحه است اجازه بده
        if (targetPath === currentPath) {
            return true;
        }
        
        // ✅ اگر صفحه مقصد هم جزو صفحات رزرو است (هدایت به صفحات دیگر رزرو)
        const isBookingPageLink = this.bookingPages.some(page => 
            targetPath.startsWith(page)
        );
        
        if (isBookingPageLink) {
            return true;
        }
        
        // در غیر این صورت پاپ‌آپ نشان بده
        return false;
    }
    showModal() {
        if (!this.popupShown) {
            this.popupShown = true;
            document.getElementById('exit-confirmation-modal').style.display = 'flex';
        }
    }
}

// اجرای خودکار
document.addEventListener('DOMContentLoaded', () => {
    window.bookingExitGuard = new BookingExitGuard();
});