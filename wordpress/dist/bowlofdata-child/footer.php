<?php
/**
 * Closing </main>, site footer, cookie banner and the inline behaviour script.
 *
 * Port of FOOTER / COOKIE_BANNER / SCRIPTS in render.mjs (lines 229-343) and of
 * templates/base.html lines 83-196.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$bod_logo = get_stylesheet_directory_uri() . '/imgs/logo.png';
?>
  </main>

  <footer class="site-footer">
    <div class="footer-inner">
      <img src="<?php echo esc_url( $bod_logo ); ?>" alt="<?php echo bod_esc( BOD_SITE_NAME ); ?>" class="footer-logo">
      <div class="footer-text">
        <p class="footer-name"><?php echo bod_esc( BOD_SITE_NAME ); ?></p>
        <p class="footer-sub"><?php echo bod_esc( BOD_SITE_TAGLINE ); ?></p>
        <p class="footer-authored">Curated by Maki &amp; reviewed by the <?php echo bod_esc( BOD_SITE_NAME ); ?> team.</p>
      </div>
      <div class="footer-social">
        <a href="https://www.instagram.com/bowl_of_data" class="footer-social-link" target="_blank" rel="noopener" aria-label="Instagram">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
            <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
            <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/>
          </svg>
        </a>
        <a href="<?php echo esc_url( BOD_SUBSTACK_URL ); ?>" class="footer-social-link" target="_blank" rel="noopener" aria-label="Subscribe on Substack">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M22.539 8.242H1.46V5.406h21.08v2.836zM1.46 10.812V24L12 18.11 22.54 24V10.812H1.46zM22.54 0H1.46v2.836h21.08V0z"/>
          </svg>
        </a>
        <a href="<?php echo esc_url( BOD_PODCAST_URL ); ?>" class="footer-social-link" target="_blank" rel="noopener" aria-label="Listen on Spotify">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141 4.32-1.32 9.719-.66 13.5 1.62.32.24.5.72.24 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.6.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.42 1.56-.299.421-1.02.599-1.559.3z"/>
        </svg>
        </a>
      </div>
      <p class="footer-credit">
        Powered by
        <a href="https://github.com/bowlofdata/maki" target="_blank" rel="noopener">Maki</a>
      </p>
    </div>
  </footer>

  <!-- Cookie consent banner -->
  <div id="cookie-banner" class="cookie-banner" role="dialog" aria-label="Cookie consent" aria-live="polite">
    <div class="cookie-banner-inner">
      <p class="cookie-banner-text">
        We use cookies and similar technologies — including Google Fonts — to operate this site.
        No advertising or tracking cookies are used.
        By clicking <strong>Accept</strong> you agree to our use of these technologies.
        <a href="https://policies.google.com/privacy" class="cookie-banner-link" target="_blank" rel="noopener">Google's privacy policy</a>.
      </p>
      <div class="cookie-banner-actions">
        <button id="cookie-accept" class="cookie-btn cookie-btn-accept">Accept</button>
        <button id="cookie-decline" class="cookie-btn cookie-btn-decline">Decline</button>
      </div>
    </div>
  </div>

  <script>
    document.documentElement.classList.add('js-anim');
    (function () {
      var btn      = document.querySelector('.menu-toggle');
      var nav      = document.querySelector('.header-nav');
      var moreBtn  = document.querySelector('.nav-more-btn');
      var morePanel = document.querySelector('.nav-more-panel');

      // Hamburger toggle
      if (btn && nav) {
        btn.addEventListener('click', function () {
          var open = nav.classList.toggle('is-open');
          btn.setAttribute('aria-expanded', String(open));
        });
      }

      // More dropdown toggle
      if (moreBtn && morePanel) {
        moreBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          var open = morePanel.classList.toggle('is-open');
          moreBtn.setAttribute('aria-expanded', String(open));
        });
        document.addEventListener('keydown', function (e) {
          if (e.key === 'Escape' && morePanel.classList.contains('is-open')) {
            morePanel.classList.remove('is-open');
            moreBtn.setAttribute('aria-expanded', 'false');
            moreBtn.focus();
          }
        });
      }

      // Close both on outside click
      document.addEventListener('click', function (e) {
        if (!e.target.closest('.header-inner') && nav && nav.classList.contains('is-open')) {
          nav.classList.remove('is-open');
          btn.setAttribute('aria-expanded', 'false');
        }
        if (!e.target.closest('.nav-more-group') && morePanel && morePanel.classList.contains('is-open')) {
          morePanel.classList.remove('is-open');
          moreBtn.setAttribute('aria-expanded', 'false');
        }
      });
    })();

    // Cookie consent
    (function () {
      var banner = document.getElementById('cookie-banner');
      if (!banner) return;
      if (!localStorage.getItem('cookie-consent')) {
        banner.classList.add('is-visible');
      }
      document.getElementById('cookie-accept').addEventListener('click', function () {
        localStorage.setItem('cookie-consent', 'accepted');
        banner.classList.remove('is-visible');
      });
      document.getElementById('cookie-decline').addEventListener('click', function () {
        localStorage.setItem('cookie-consent', 'declined');
        banner.classList.remove('is-visible');
      });
    })();
  </script>
<?php wp_footer(); ?>
</body>
</html>
