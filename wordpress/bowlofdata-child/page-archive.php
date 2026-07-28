<?php
/**
 * Archive index — /archive.html
 *
 * Port of renderArchive() in render.mjs (lines 747-844) / templates/archive.html.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$issues      = bod_all_issues();
$years       = bod_group_issues_by_year_month( $issues );
$total_count = count( $issues );

bod_page_context(
	array(
		'title'        => 'Archive · ' . BOD_SITE_NAME,
		'description'  => 'Browse every past issue of Bowl of Data, the weekly tech newsletter covering AI, cybersecurity, blockchain, and engineering.',
		'og_type'      => 'website',
		'canonical'    => bod_canonical( '/archive.html' ),
		'current_page' => 'archive',
		'jsonld'       => array( bod_website_jsonld() ),
	)
);

get_header();

$is_first = true;
?>
<div class="archive-header">
  <div class="archive-header-inner">
    <div class="archive-header-text">
      <h1 class="archive-title">All issues</h1>
      <p class="archive-sub">Every weekly digest, from the first bowl to the latest.</p>
    </div>
<?php if ( $total_count ) : ?>
    <div class="archive-header-stat">
      <span class="archive-stat-num"><?php echo (int) $total_count; ?></span>
      <span class="archive-stat-label">issue<?php echo esc_html( bod_plural( $total_count ) ); ?></span>
    </div>
<?php endif; ?>
  </div>
</div>

<?php if ( ! $years ) : ?>
<div class="section">
  <p class="empty-state">No newsletters found yet. Run the Maki pipeline to generate the first issue.</p>
</div>
<?php else : ?>

<?php if ( count( $years ) > 1 ) : ?>
<div class="archive-year-nav">
  <div class="archive-year-nav-inner">
    <span class="archive-year-nav-label">Jump to</span>
    <?php foreach ( $years as $yg ) : ?>
    <a href="#year-<?php echo (int) $yg['year']; ?>" class="archive-year-pill"><?php echo (int) $yg['year']; ?></a>
    <?php endforeach; ?>
  </div>
</div>
<?php endif; ?>

<div class="archive-body">
<?php foreach ( $years as $yg ) : ?>
  <section class="archive-year-section" id="year-<?php echo (int) $yg['year']; ?>">

    <div class="archive-year-band">
      <div class="archive-year-band-inner">
        <span class="archive-year-label"><?php echo (int) $yg['year']; ?></span>
        <span class="archive-year-count"><?php echo (int) $yg['count']; ?> issue<?php echo esc_html( bod_plural( $yg['count'] ) ); ?></span>
      </div>
    </div>

<?php foreach ( $yg['months'] as $mg ) : ?>
    <div class="archive-month-section">
      <div class="archive-month-header">
        <span class="archive-month-name"><?php echo esc_html( $mg['month_name'] ); ?></span>
        <span class="archive-month-count"><?php echo count( $mg['weeks'] ); ?> issue<?php echo esc_html( bod_plural( count( $mg['weeks'] ) ) ); ?></span>
      </div>
      <div class="week-grid">
<?php
foreach ( $mg['weeks'] as $wk ) :
	$latest   = $is_first;
	$is_first = false;
	?>
        <a class="week-card<?php echo $latest ? ' week-card-latest' : ''; ?>" href="<?php echo esc_url( bod_url( '/' . $wk['href'] ) ); ?>">
          <?php echo $latest ? '<span class="week-card-badge">Latest</span>' : ''; ?>
          <div class="week-card-label"><?php echo esc_html( $wk['label'] ); ?></div>
          <div class="week-card-count"><?php echo (int) $wk['article_count']; ?> articles</div>
<?php if ( ! empty( $wk['preview_titles'] ) ) : ?>
          <ul class="week-card-preview">
            <?php foreach ( $wk['preview_titles'] as $pt ) : ?>
            <li><?php echo esc_html( $pt ); ?></li>
            <?php endforeach; ?>
          </ul>
<?php endif; ?>
        </a>
<?php endforeach; ?>
      </div>
    </div>
<?php endforeach; ?>

  </section>
<?php endforeach; ?>
</div>

<?php endif; ?>
<?php
get_footer();
