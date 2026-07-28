<?php
/**
 * One weekly issue — /week/30_2026.html
 *
 * Port of renderWeek() in render.mjs (lines 521-656) / templates/week.html.
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

$issue = bod_issue_data( get_queried_object_id() );
if ( ! $issue ) {
	status_header( 404 );
	include get_query_template( '404' );
	return;
}

$articles = bod_issue_stories( $issue['id'], 'article' );
$papers   = bod_issue_stories( $issue['id'], 'paper' );
$releases = bod_issue_releases( $issue['id'] );
$linkable = bod_linkable_tag_slugs();

$sort_key = (int) get_post_meta( $issue['id'], 'bod_sort_key', true );
$prev     = bod_adjacent_issue( $sort_key, 'prev' );
$next     = bod_adjacent_issue( $sort_key, 'next' );

$week2 = sprintf( '%02d', $issue['week'] );

$meta = count( $articles ) . ' article' . bod_plural( count( $articles ) );
if ( $releases ) {
	$meta .= ' · ' . count( $releases ) . ' model release' . bod_plural( count( $releases ) );
}
if ( $papers ) {
	$meta .= ' · ' . count( $papers ) . ' paper' . bod_plural( count( $papers ) );
}

bod_page_context(
	array(
		'title'        => $issue['label'] . ' · ' . BOD_SITE_NAME,
		'description'  => count( $articles ) . ' article' . bod_plural( count( $articles ) ) . ' curated this week: AI, cybersecurity, blockchain and engineering.',
		'og_type'      => 'article',
		'canonical'    => bod_canonical( '/' . $issue['href'] ),
		'current_page' => null, // Week pages highlight no nav item, matching the Python build.
		'jsonld'       => array(
			bod_week_jsonld( $issue, $articles ),
			bod_breadcrumb_jsonld(
				array(
					array( BOD_SITE_NAME, BOD_CANONICAL_ORIGIN . '/' ),
					array( 'Archive', BOD_CANONICAL_ORIGIN . '/archive.html' ),
					array( $issue['label'], BOD_CANONICAL_ORIGIN . '/' . $issue['href'] ),
				)
			),
		),
	)
);

/** Prev/next button, or an empty span to hold the grid column. */
$bod_nav_btn = static function ( $target, $class, $label_fmt ) {
	if ( ! $target ) {
		return '<span></span>';
	}
	return '<a href="' . esc_url( bod_url( '/' . $target['href'] ) ) . '" class="week-nav-btn ' . $class . '">'
		. sprintf( $label_fmt, bod_esc( $target['label'] ) ) . '</a>';
};

get_header();
?>
<div class="week-header">
  <div class="week-header-inner">
    <a href="<?php echo esc_url( bod_url( '/archive.html' ) ); ?>" class="back-link">← All issues</a>
    <h1 class="week-title">
      Week <span class="week-title-accent"><?php echo esc_html( $week2 ); ?></span> · <?php echo (int) $issue['year']; ?>
    </h1>
    <p class="week-meta"><?php echo esc_html( $meta ); ?></p>
<?php if ( $prev || $next ) : ?>
    <div class="week-nav week-nav--header">
      <?php echo $bod_nav_btn( $prev, 'week-nav-older', '← %s' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
      <?php echo $bod_nav_btn( $next, 'week-nav-newer', '%s →' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
    </div>
<?php endif; ?>
  </div>
</div>

<?php if ( $releases ) : ?>
<section class="releases-section">

  <div class="releases-header">
    <div class="releases-header-inner">
      <div class="releases-header-text">
        <h2 class="releases-title">AI Model Releases</h2>
        <p class="releases-sub">New models and updates from major AI providers this week</p>
      </div>
      <span class="releases-badge">This Week</span>
    </div>
  </div>

  <div class="releases-body">
    <div class="releases-body-inner">
      <div class="releases-grid">
<?php
foreach ( $releases as $release ) {
	echo bod_release_card( $release ) . "\n"; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- escaped inside.
}
?>
      </div>
    </div>
  </div>

</section>
<?php endif; ?>

<?php if ( $papers ) : ?>
<section class="papers-section">

  <div class="releases-header">
    <div class="releases-header-inner">
      <div class="releases-header-text">
        <h2 class="releases-title">Research Papers</h2>
        <p class="releases-sub">Selected arXiv and HuggingFace papers this week</p>
      </div>
      <span class="releases-badge papers-badge">This Week</span>
    </div>
  </div>

  <div class="releases-body">
    <div class="article-section">
      <div class="article-list">
<?php
foreach ( $papers as $i => $paper ) {
	echo bod_article_card( $paper, $i + 1, 'Paper', 'Read paper', $linkable ) . "\n"; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
}
?>
      </div>
    </div>
  </div>

</section>
<?php endif; ?>

<section class="news-section">

  <div class="releases-header news-section-band">
    <div class="releases-header-inner">
      <div class="releases-header-text">
        <h2 class="releases-title">This Week in Tech</h2>
        <p class="releases-sub">Top stories curated from across the web this week</p>
      </div>
      <span class="releases-badge news-badge">This Week</span>
    </div>
  </div>

  <div class="article-section">
<?php if ( $articles ) : ?>
    <div class="article-list">
<?php
foreach ( $articles as $i => $article ) {
	echo bod_article_card( $article, $i + 1, 'Article', 'Read full article', $linkable ) . "\n"; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
}
?>
    </div>

    <div class="week-nav week-nav-bottom-bar">
      <?php echo $bod_nav_btn( $prev, 'week-nav-older', '← %s' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
      <a href="<?php echo esc_url( bod_url( '/archive.html' ) ); ?>" class="week-nav-btn week-nav-archive">All issues</a>
      <?php echo $bod_nav_btn( $next, 'week-nav-newer', '%s →' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?>
    </div>
<?php else : ?>
    <p class="empty-state">No articles in this issue.</p>
<?php endif; ?>
  </div>

</section>
<?php
echo bod_subscribe_cta( 'week' ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
get_footer();
