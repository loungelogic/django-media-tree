/**
 *  jQuery Avgrund Popin Plugin
 *  http://github.com/voronianski/jquery.avgrund.js/
 *
 *  (c) 2012-2013 http://pixelhunter.me/
 *  MIT licensed
 */

(function (factory) {
	if (typeof define === 'function' && define.amd) {
		// AMD
		define(['jquery'], factory);
	} else if (typeof exports === 'object') {
		// CommonJS
		module.exports = factory;
	} else {
		// Browser globals
		factory(django.jQuery);
	}
}(function ($) {
	$.fn.avgrund = function (options) {
		var defaults = {
			width: 380,
			height: 280,
			showClose: false,
			showCloseText: '',
			closeByEscape: true,
			closeByDocument: true,
			holderClass: '',
			overlayClass: '',
			enableStackAnimation: false,
			onBlurContainer: '',
			openOnEvent: true,
			setEvent: 'click',
			beforeLoad: false,
			afterLoad: false,
			onUnload: false,
			template: ''
		};

		options = $.extend(defaults, options);

		return this.each(function() {
			var self = $(this),
				body = $('body'),
				maxWidth = options.width,
				maxHeight = options.height,
				template = typeof options.template === 'function' ?
					options.template(self) :
					options.template instanceof jQuery ?
						options.template.html() :
						options.template;

			body.addClass('avgrund-ready');
			body.append('<div class="avgrund-overlay ' + options.overlayClass + '"></div>');

			if (options.onBlurContainer !== '') {
				$(options.onBlurContainer).addClass('avgrund-blur');
			}

			function onDocumentKeyup (e) {
				if (options.closeByEscape) {
					if (e.keyCode === 27) {
						deactivate();
					}
				}
			}

			function onDocumentClick (e) {
				if (options.closeByDocument) {
					if ($(e.target).is('.avgrund-overlay, .avgrund-close')) {
						e.preventDefault();
						deactivate();
					}
				} else if ($(e.target).is('.avgrund-close')) {
						e.preventDefault();
						deactivate();
				}
			}

			function activate () {
				if (typeof options.beforeLoad === 'function') {
					options.beforeLoad(self);
				}

				setTimeout(function() {
					body.addClass('avgrund-active');
				}, 100);

				body.append('<div class="avgrund-popin ' + options.holderClass + '">' + template + '</div>');


				if (options.showClose) {
					$('.avgrund-popin').append('<a href="#" class="avgrund-close">' + options.showCloseText + '</a>');
				}

				if (options.enableStackAnimation) {
					$('.avgrund-popin').addClass('stack');
				}

				body.bind('keyup', onDocumentKeyup)
					.bind('click', onDocumentClick);

				if (typeof options.afterLoad === 'function') {
					options.afterLoad(self);
				}
			}

			function deactivate () {
				body.unbind('keyup', onDocumentKeyup)
					.unbind('click', onDocumentClick)
					.removeClass('avgrund-active');

				setTimeout(function() {
					$('.avgrund-popin').remove();
				}, 500);

				if (typeof options.onUnload === 'function') {
					options.onUnload(self);
				}
			}

			if (options.openOnEvent) {
				self.bind(options.setEvent, function (e) {
					e.stopPropagation();

					if ($(e.target).is('a')) {
						e.preventDefault();
					}

					activate();
				});
			} else {
				activate();
			}
		});
	};
}));
