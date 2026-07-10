//  مدیریت خروج از فرآیند رزرو

// یه تابع کمکی برای اینکه وقتی کاربر روی دکمه‌های دراپ‌داون (مثل منوی پروفایل) کلیک کرد، 
// سیستم فکر نکنه طرف میخواد از صفحه بره بیرون.
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
        //لیست آدرس‌هایی که جزو مراحل رزرو حساب میشن
        this.bookingPages = [
            '/reserve',
            '/select-date',
            '/contact-info',
            '/payment-confirm'
        ];
        // چک میکنیم ببینیم اصلا الان تو یکی از صفحات رزرو هستیم یا نه
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
        this.attachBackButtonListener();     // مدیریت دکمه بکِ خود مرورگر
    }

    createModal() {
        // اگه مدال از قبل تو صفحه هست که هیچی، دوباره نمیسازیمش
        if (document.getElementById('exit-confirmation-modal')) return;

        // ظاهر مدال رو همینجا با جاوا اسکریپت می‌سازیم و میندازیمش ته body
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
        //هر دکمه توی مدال چه کاری باید انجام بده
        document.getElementById('close-exit-modal').onclick = () => this.closeModal();
        document.getElementById('btn-stay').onclick = () => this.closeModal();      // پشیمون شد، می‌خواد بمونه
        document.getElementById('btn-exit').onclick = () => this.confirmExit();     // واقعاً می‌خواد بره
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
            //وقتی کار بک اند تموم شد، کاربر رو میفرستیم به همون لینکی که از اول میخواست بره
            if (this.exitTargetUrl) {
                window.location.href = this.exitTargetUrl;
            } else {
                window.location.href = '/'; // اگه لینکی نبود، بندازش صفحه اصلی
            }
        });
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
    }

    attachLinkListeners() {
        // ۱. شنود تمام لینک‌های <a> تو صفحه
        document.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', (e) => {
                // اگه این لینک مجازه (مثلا دکمه‌های داخلی خود فرآیند رزروه)، کاریش نداشته باش
                if (this.shouldAllowNavigation(link)) {
                    this.allowBrowserUnload = true; 
                    return;
                }

                // در غیر این صورت، جلوی رفتنش رو بگیر و پاپ‌آپ رو نشون بده
                e.preventDefault();
                this.exitTargetUrl = link.href;
                this.showModal();
            });
        });
        
        // ۲. شنود دکمه زنگوله (اعلانات)
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
        
        // ۴. آیتم‌های داخل همون منوی کشویی پروفایل
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
                this.popupShown = true;  // با این کار، موقع رفرش شدن صفحه واسه سابمیت، اخطار نمیده
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

    //اینجا تصمیم میگیریم که با کلیک روی یه دکمه، اخطار بدیم یا نه
    shouldAllowNavigation(element) {
        //  اگر عنصر دکمه خاص رزرو است (مثل انتخاب سرویس)
        //  اگه خودمون به دکمه گفتیم data-no-exit یعنی کاری به کارش نداشته باش
        if (element.hasAttribute('data-no-exit') || 
            element.classList.contains('booking-exit-link')) {
            return true;
        }
        
        //  اگه کلیک روی یه دکمه‌ای داخل فرم بوده
        if (element.closest('form')) {
            return true;
        }
        
        //  اگه لینک از نوع anchor (پیمایش تو همون صفحه با #) هست
        if (element.getAttribute('href') && element.getAttribute('href').startsWith('#')) {
            return true;
        }
        
        //  دریافت مسیر مقصد
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
        
         // اگه اصلا لینکی نداره، بی‌خیالش شو
        if (!targetUrl || targetUrl.trim() === '') {
            return true;
        }
        
        // مسیر الانمون چیه و کجا میخواد بره
        const currentPath = window.location.pathname;
        let targetPath = '';
        
        try {
            targetPath = new URL(targetUrl, window.location.origin).pathname;
        } catch {
            targetPath = targetUrl;
        }
        
        // اگه داره به همون صفحه‌ای که توش هستیم رفرش میشه
        if (targetPath === currentPath) {
            return true;
        }
        
        //  اگه داره میره به مرحله بعدی یا قبلی رزرو (یعنی هنوز تو چرخه رزرو هست)
        const isBookingPageLink = this.bookingPages.some(page => 
            targetPath.startsWith(page)
        );
        
        if (isBookingPageLink) {
            return true;
        }
        
        // اگه به هیچ کدوم از شرط‌های بالا نخورد،  پاپ‌آپ رو بیار بالا.
        return false;
    }
    showModal() {
        if (!this.popupShown) {
            this.popupShown = true;
            document.getElementById('exit-confirmation-modal').style.display = 'flex';
        }
    }
}

// وقتی کل HTML صفحه لود شد، گارد ما استارت میخوره
document.addEventListener('DOMContentLoaded', () => {
    window.bookingExitGuard = new BookingExitGuard();
});