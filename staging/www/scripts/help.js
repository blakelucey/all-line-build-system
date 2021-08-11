var toggle_form_group = function () {
   if ($(this).hasClass('is-visible')) {
      $(this).next('div').slideUp(500);
      $(this).removeClass('is-visible').addClass('is-not-visible');
   }
   else {
      $(this).next('div').slideDown(500);
      $(this).removeClass('is-not-visible').addClass('is-visible');
   }
}

$(function () {
   $('.form-header.can-toggle').each(function () {
      $(this).click(toggle_form_group);
      $(this).next('div').hide();
      $(this).addClass('is-not-visible');
   });

   $('.has-help').each(function () {
      errors = $(this).next('div.arrow_box').next('div.form-error');
      if (errors.length) return;
      $(this).on('focus', function () {
         help = $(this).nextAll('div.arrow_box');
         help.fadeIn(250).css('display', 'inline-block');
      }).on('blur', function () {
         help = $(this).nextAll('div.arrow_box');
         help.fadeOut(250).css('display', 'inline-block');
      });
   });
});
