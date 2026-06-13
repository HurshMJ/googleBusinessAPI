/*!
 * Sitepackage v1.0.0 (https://ihr-layout.eu)
 * Copyright 2017-2028 Michael Müller
 * Licensed under the GPL-2.0-or-later license
 */
//console.log('WE LOVE TYPO3');

(function ($) {
  'use strict';

/*$('.navbar-toggler-clone').click(function () {
	$( 'body' ).removeClass( 'navbar-collapse-show' );
});*/
	
	$(document).ready(function () {
    function setEqualHeight() {
        var maxHeight = 475;

        // Höhe der höchsten .equal-height Div finden
        $('.equal-height').each(function () {
            $(this).css('height', 'auto'); // Setzt die Höhe zurück, um korrekte Messung zu gewährleisten
            var thisHeight = $(this).outerHeight();
            if (thisHeight > maxHeight) {
                maxHeight = thisHeight;
            }
        });

        // Alle .equal-height Divs auf die maximale Höhe setzen
        $('.equal-height').height(maxHeight);
    }

    setEqualHeight(); // Gleich nach dem Laden ausführen

		
document.querySelectorAll('#language_menu a').forEach(link => {
    link.addEventListener('click', () => {
      const collapse = document.querySelector('#language-wrapper');
      if (collapse.classList.contains('show')) {
        const bsCollapse = bootstrap.Collapse.getInstance(collapse) || new bootstrap.Collapse(collapse);
        bsCollapse.hide();
      }
    });
  });
		
    $(window).resize(function () {
        setEqualHeight();
    });
		
		  $('#tab-325 button').click(function (e) {
                e.preventDefault()
                $(this).tab('show')
            })

            $('button[data-toggle="tab"]').on('shown.bs.tab', function (e) {
                e.relatedTarget // previous tab
            });
        
	
});
	
}) (jQuery);