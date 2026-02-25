document.addEventListener("DOMContentLoaded", function () {

  document.querySelectorAll("form").forEach(function(form){

    form.addEventListener("submit", function(){

      const submitBtn = form.querySelector("button[type='submit']");

      if (!submitBtn) return;

      // اگر قبلاً غیرفعال شده کاری نکن
      if (submitBtn.disabled) return;

      submitBtn.disabled = true;

      // ذخیره متن اصلی
      const originalHTML = submitBtn.innerHTML;

      submitBtn.setAttribute("data-original-text", originalHTML);

      // تغییر متن
      submitBtn.innerHTML =
        '<i class="fas fa-spinner fa-spin me-2"></i>در حال پردازش...';

    });

  });

});
