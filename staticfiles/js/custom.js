// static/js/custom.js

// تفعيل التلميحات tooltips
$(function () {
    $('[data-toggle="tooltip"]').tooltip();
});

// تفعيل القوائم المنسدلة
$(document).ready(function() {
    $('.dropdown-toggle').dropdown();
});

// تغيير اللغة عند اختيار لغة جديدة من القائمة
$(document).ready(function() {
    $('#language').change(function() {
        var selectedLanguage = $(this).val();
        // تقديم نموذج تغيير اللغة المطابق
        $('form input[value="' + selectedLanguage + '"]').closest('form').submit();
    });
});

// تشغيل المقطع الصوتي عند النقر على الزر
$(document).ready(function() {
    $('.play-segment').click(function() {
        var audio = document.getElementById('audioPlayer');
        var startTime = $(this).data('start');
        audio.currentTime = startTime;
        audio.play();
    });
});

// تمييز المقطع النصي الحالي أثناء تشغيل الصوت
$(document).ready(function() {
    var audio = document.getElementById('audioPlayer');
    if (audio) {
        audio.ontimeupdate = function() {
            var currentTime = audio.currentTime;
            $('.transcript-segment').each(function() {
                var start = $(this).data('start');
                var end = $(this).data('end');

                if (currentTime >= start && currentTime <= end) {
                    $(this).addClass('bg-light');
                } else {
                    $(this).removeClass('bg-light');
                }
            });
        };
    }
});