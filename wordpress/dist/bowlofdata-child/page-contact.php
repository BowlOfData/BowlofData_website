<?php
/**
 * Contact — /contact.html
 *
 * Port of templates/contact.html. Same markup and same thank-you/error states;
 * the fetch target moves from Netlify Forms to admin-ajax (see inc/contact.php).
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

bod_page_context(
	array(
		'title'        => 'Contact · ' . BOD_SITE_NAME,
		'description'  => 'Get in touch with the Bowl of Data team — feedback, article suggestions, or questions about our weekly tech newsletter.',
		'og_type'      => 'website',
		'canonical'    => bod_canonical( '/contact.html' ),
		'current_page' => 'contact',
	)
);

get_header();
?>
<div class="contact-header">
  <div class="contact-header-inner">
    <h1 class="contact-title">Get in touch</h1>
    <p class="contact-sub">Feedback, article suggestions, or anything else; we read every message.</p>
  </div>
</div>

<div class="contact-body">
  <div class="contact-grid">

    <!-- Form -->
    <div class="contact-form-wrap">

      <!-- Thank-you state -->
      <div class="contact-thankyou" id="contact-thankyou" hidden>
        <p class="thankyou-icon">&#10003;</p>
        <h2 class="thankyou-title">Message sent!</h2>
        <p class="thankyou-sub">Thanks for reaching out. We'll get back to you as soon as possible.</p>
        <a href="<?php echo esc_url( bod_url( '/' ) ); ?>" class="thankyou-home">Back to home</a>
      </div>

      <!-- Error banner -->
      <div class="contact-error" id="contact-error" hidden>
        <p>Something went wrong. Please try again in a moment.</p>
      </div>

      <form
        id="contact-form"
        name="contact"
        method="POST"
        action="<?php echo esc_url( admin_url( 'admin-ajax.php' ) ); ?>"
        class="contact-form"
      >
        <input type="hidden" name="action" value="bod_contact">
        <input type="hidden" name="bod_nonce" value="<?php echo esc_attr( wp_create_nonce( 'bod_contact' ) ); ?>">
        <p hidden><input name="bot-field"></p>

        <div class="form-group">
          <label class="form-label" for="name">Name</label>
          <input
            class="form-input"
            type="text"
            id="name"
            name="name"
            placeholder="Your name"
            required
          >
        </div>

        <div class="form-group">
          <label class="form-label" for="email">Email</label>
          <input
            class="form-input"
            type="email"
            id="email"
            name="email"
            placeholder="you@example.com"
            required
          >
        </div>

        <div class="form-group">
          <label class="form-label" for="subject">Subject</label>
          <select class="form-input form-select" id="subject" name="subject">
            <option value="feedback">Feedback</option>
            <option value="article-suggestion">Article suggestion</option>
            <option value="partnership">Partnership</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label" for="message">Message</label>
          <textarea
            class="form-input form-textarea"
            id="message"
            name="message"
            placeholder="What's on your mind?"
            rows="6"
            required
          ></textarea>
        </div>

        <button type="submit" class="form-submit" id="form-submit-btn">Send message</button>
      </form>
    </div>

    <!-- Info panel -->
    <aside class="contact-info">
      <div class="contact-info-card">
        <h2 class="info-title">What to expect</h2>
        <ul class="info-list">
          <li class="info-item">
            <span class="info-dot info-dot-yellow"></span>
            <div>
              <p class="info-item-label">Response time</p>
              <p class="info-item-text">We reply within a few days, usually sooner.</p>
            </div>
          </li>
          <li class="info-item">
            <span class="info-dot info-dot-orange"></span>
            <div>
              <p class="info-item-label">Article suggestions</p>
              <p class="info-item-text">Got a story we should cover? Drop the URL and a line on why it matters.</p>
            </div>
          </li>
          <li class="info-item">
            <span class="info-dot info-dot-amber"></span>
            <div>
              <p class="info-item-label">Feedback</p>
              <p class="info-item-text">Tell us what you love, what you'd cut, or what you'd add.</p>
            </div>
          </li>
        </ul>
      </div>
    </aside>

  </div>
</div>

<script>
  (function () {
    var form    = document.getElementById('contact-form');
    var thankyou = document.getElementById('contact-thankyou');
    var errorBanner = document.getElementById('contact-error');
    var submitBtn = document.getElementById('form-submit-btn');

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      // Loading state
      submitBtn.disabled = true;
      submitBtn.textContent = 'Sending…';
      errorBanner.hidden = true;

      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        credentials: 'same-origin'
      })
        .then(function (response) {
          if (!response.ok) throw new Error('status ' + response.status);
          return response.json();
        })
        .then(function (data) {
          if (data && data.success) {
            form.hidden = true;
            thankyou.hidden = false;
          } else {
            throw new Error('rejected');
          }
        })
        .catch(function () {
          submitBtn.disabled = false;
          submitBtn.textContent = 'Send message';
          errorBanner.hidden = false;
          errorBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        });
    });
  })();
</script>
<?php
get_footer();
