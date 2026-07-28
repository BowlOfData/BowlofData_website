<?php
/**
 * Home — /
 *
 * Port of templates/index.html.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$issues       = bod_all_issues();
$total_count  = count( $issues );
$latest       = $issues ? $issues[0] : null;
$recent       = array_slice( $issues, 1, 5 );
$total_arts   = bod_total_articles();
$latest_prev  = array();

if ( $latest ) {
	// The hero card lists the first three headlines of the latest issue.
	$stories = bod_issue_stories( $latest['id'], 'article' );
	$latest_prev = array_slice( $stories, 0, 3 );
}

bod_page_context(
	array(
		'title'        => BOD_SITE_NAME . ' — Weekly AI, Security & Tech Newsletter',
		'description'  => 'Bowl of Data is a weekly tech newsletter covering AI, cybersecurity, blockchain, and engineering — curated by an AI-powered pipeline that reads hundreds of sources so you don\'t have to.',
		'og_type'      => 'website',
		'canonical'    => bod_canonical( '/' ),
		'current_page' => 'home',
		'jsonld'       => array( bod_website_jsonld() ),
	)
);

get_header();
?>
<section class="hero" aria-label="Bowl of Data — weekly tech digest">
  <div class="hero-inner">
    <div class="hero-copy">
<?php if ( $total_count ) : ?>
      <p class="hero-stat-line">
        <span class="hero-stat"><strong><?php echo (int) $total_count; ?></strong> issues shipped</span>
        <span class="hero-stat"><strong><?php echo esc_html( number_format_i18n( $total_arts ) ); ?></strong> stories filtered</span>
        <span class="hero-stat"><strong>Sat</strong> every week</span>
      </p>
<?php endif; ?>
      <h1 class="hero-headline">
        The feed is noise.
        <span class="hero-headline-accent">We serve the <span class="mark">signal</span>.</span>
      </h1>
      <p class="hero-sub">
        Bowl of Data reads hundreds of sources every week — model releases, security
        advisories, blockchain moves, engineering deep-dives — and hands you
        <em>only the stories worth your time</em>.
      </p>
      <div class="hero-ctas">
        <a href="<?php echo esc_url( BOD_SUBSTACK_URL ); ?>" class="cta-primary" target="_blank" rel="noopener">Subscribe — it's free</a>
<?php if ( $latest ) : ?>
        <a href="<?php echo esc_url( bod_url( '/' . $latest['href'] ) ); ?>" class="cta-secondary">Read issue <?php echo (int) $latest['week']; ?> →</a>
<?php endif; ?>
        <a href="<?php echo esc_url( bod_url( '/archive.html' ) ); ?>" class="cta-secondary">Browse archive</a>
      </div>
    </div>

<?php if ( $latest ) : ?>
    <aside class="manifest" aria-label="Latest issue">
      <div class="manifest-top">
        <div>
          <p class="manifest-label">Latest issue</p>
          <div class="manifest-issue">
            <span class="manifest-num"><?php echo (int) $latest['week']; ?></span><span class="manifest-yr">/<?php echo (int) $latest['year']; ?></span>
          </div>
        </div>
        <div class="manifest-meta">
          <div class="manifest-count"><?php echo (int) $latest['article_count']; ?><span>stories</span></div>
        </div>
      </div>

      <div class="beats">
        <div class="beat beat-ai"><i></i><span class="nm">AI &amp; ML</span></div>
        <div class="beat beat-chain"><i></i><span class="nm">Blockchain</span></div>
        <div class="beat beat-sec"><i></i><span class="nm">Security</span></div>
        <div class="beat beat-eng"><i></i><span class="nm">Engineering</span></div>
      </div>

<?php if ( $latest_prev ) : ?>
      <ol class="tock">
<?php foreach ( $latest_prev as $i => $story ) : ?>
        <li><span class="ix"><?php echo esc_html( sprintf( '%02d', $i + 1 ) ); ?></span><span class="tt"><?php echo esc_html( $story['title'] ); ?></span></li>
<?php endforeach; ?>
      </ol>
<?php endif; ?>

      <a class="manifest-cta" href="<?php echo esc_url( bod_url( '/' . $latest['href'] ) ); ?>">Read the full plate →</a>
    </aside>
<?php endif; ?>
  </div>
</section>

<section class="band">
  <div class="band-inner">
    <div class="band-head">
      <h2 class="band-title">What&rsquo;s in the bowl</h2>
      <span class="eyebrow">Four beats, every issue</span>
    </div>
    <div class="cov">
      <a class="cov-item cov-ai" href="<?php echo esc_url( bod_url( '/topic/ai.html' ) ); ?>">
        <p class="cov-k">Intelligence</p>
        <h3 class="cov-n">AI &amp; Machine Learning</h3>
        <p class="cov-d">Model releases, research that holds up, and where large models actually land in products and people.</p>
      </a>
      <a class="cov-item cov-sec" href="<?php echo esc_url( bod_url( '/topic/security.html' ) ); ?>">
        <p class="cov-k">Defense</p>
        <h3 class="cov-n">Cybersecurity</h3>
        <p class="cov-d">Vulnerabilities, exploits, threat intel, and what to patch before it becomes someone else&rsquo;s headline.</p>
      </a>
      <a class="cov-item cov-chain" href="<?php echo esc_url( bod_url( '/topic/blockchain.html' ) ); ?>">
        <p class="cov-k">Ledger</p>
        <h3 class="cov-n">Blockchain &amp; Crypto</h3>
        <p class="cov-d">Protocol upgrades, market moves, DeFi developments, and the regulatory shifts worth watching.</p>
      </a>
      <a class="cov-item cov-eng" href="<?php echo esc_url( bod_url( '/topic/engineering.html' ) ); ?>">
        <p class="cov-k">Craft</p>
        <h3 class="cov-n">Software Engineering</h3>
        <p class="cov-d">Tools, frameworks, and open-source releases that change how we build things.</p>
      </a>
    </div>
  </div>
</section>

<?php if ( $recent ) : ?>
<section class="band">
  <div class="band-inner">
    <div class="band-head">
      <h2 class="band-title">The register</h2>
      <span class="eyebrow">Indexed by ISO week</span>
    </div>
    <div class="reg">
<?php foreach ( $recent as $w ) : ?>
      <a class="reg-row" href="<?php echo esc_url( bod_url( '/' . $w['href'] ) ); ?>">
        <span class="reg-wk"><?php echo (int) $w['week']; ?></span>
        <span class="reg-lbl"><?php echo esc_html( $w['label'] ); ?></span>
        <span class="reg-cnt"><b><?php echo (int) $w['article_count']; ?></b> stories</span>
      </a>
<?php endforeach; ?>
    </div>
    <div class="reg-foot">
      <a class="cta-secondary" href="<?php echo esc_url( bod_url( '/archive.html' ) ); ?>">Browse all <?php echo (int) $total_count; ?> issues →</a>
    </div>
  </div>
</section>
<?php endif; ?>
<?php
get_footer();
