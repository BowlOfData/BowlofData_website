<?php
/**
 * Markup renderers — the PHP port of netlify/functions/_shared/render.mjs.
 *
 * Function-for-function transliteration so the two stay comparable:
 *   esc()          -> bod_esc()
 *   slugify()      -> bod_slugify()
 *   articleCard()  -> bod_article_card()
 *   releaseCard()  -> bod_release_card()
 *   subscribeCta() -> bod_subscribe_cta()
 *   *Jsonld()      -> bod_*_jsonld()
 *   shell()        -> header.php + footer.php
 *
 * One deliberate difference: render.mjs threads a relative `prefix` through
 * every link because it writes files at two directory depths. WordPress serves
 * from a router, so links here are absolute via bod_url().
 *
 * @package bowlofdata
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Escape exactly as Jinja2/markupsafe does (note &#39; and &#34;). */
function bod_esc( $value ) {
	if ( null === $value ) {
		return '';
	}
	return str_replace(
		array( '&', '<', '>', "'", '"' ),
		array( '&amp;', '&lt;', '&gt;', '&#39;', '&#34;' ),
		(string) $value
	);
}

/** Port of build.py _slugify. Keep in step — tag URLs depend on it. */
function bod_slugify( $text ) {
	$slug = strtolower( trim( (string) $text ) );
	$slug = preg_replace( '/[^\w\s-]/u', '', $slug );
	$slug = preg_replace( '/[\s_]+/u', '-', $slug );
	$slug = preg_replace( '/-+/', '-', $slug );
	return trim( $slug, '-' );
}

/** "" or "s". */
function bod_plural( $n ) {
	return 1 !== (int) $n ? 's' : '';
}

/** YYYY-MM-DD (UTC) from epoch seconds. */
function bod_date_from_mtime( $mtime ) {
	if ( ! $mtime ) {
		return null;
	}
	return gmdate( 'Y-m-d', (int) $mtime );
}

/** Absolute URL on this install: bod_url('/tag/python.html'). */
function bod_url( $path = '/' ) {
	return home_url( $path );
}

/**
 * The canonical twin of a path. See BOD_CANONICAL_ORIGIN in functions.php.
 */
function bod_canonical( $path = '/' ) {
	return BOD_CANONICAL_ORIGIN . '/' . ltrim( $path, '/' );
}

/**
 * Absolute URL of a theme image.
 *
 * Always served from this install rather than from BOD_CANONICAL_ORIGIN . '/imgs/'.
 * That path only exists on the Netlify build; pointed at .net it 301s to a
 * homepage, so og:image, the favicon and the JSON-LD logo were all resolving to
 * an HTML document. An og:image does not need to share an origin with the page.
 */
function bod_image_url( $name ) {
	return get_stylesheet_directory_uri() . '/imgs/' . ltrim( $name, '/' );
}

/**
 * The feed this site advertises.
 *
 * A mirror defers to the canonical origin's feed; a self-canonical install has
 * no feed there to defer to, so WordPress's own is the right one.
 */
function bod_feed_url() {
	return BOD_IS_MIRROR ? BOD_CANONICAL_ORIGIN . '/feed.xml' : get_feed_link();
}

/** JSON for a ld+json block. */
function bod_json( $data ) {
	return wp_json_encode( $data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
}

// ---------------------------------------------------------------------------
// Page context — set by a template before get_header() so the shell can use it
// ---------------------------------------------------------------------------

/**
 * Stash the head/nav context for the current request.
 *
 * The defaults apply on read as well as on write. A template that never calls
 * the setter — anything falling through to index.php — must still hand
 * header.php a complete context, or the page ships an empty <title> and an
 * empty rel=canonical.
 *
 * @param array $context title, description, og_type, canonical, current_page, jsonld[].
 */
function bod_page_context( $context = null ) {
	static $current = null;

	if ( is_array( $context ) || null === $current ) {
		// An empty canonical means "emit no <link rel=canonical>". Every real
		// template passes one; what falls through to index.php is content with
		// no bowlofdata.net twin, and pointing it at a .net URL that 404s would
		// be worse than staying silent. Those pages are noindex anyway (inc/seo.php).
		$defaults = array(
			'title'        => BOD_SITE_NAME,
			'description'  => BOD_SITE_TAGLINE,
			'og_type'      => 'website',
			'canonical'    => '',
			'current_page' => null,
			'jsonld'       => array(),
		);

		$current = is_array( $context ) ? wp_parse_args( $context, $defaults ) : $defaults;
	}

	return $current;
}

// ---------------------------------------------------------------------------
// JSON-LD (ports of build.py _make_*_jsonld)
// ---------------------------------------------------------------------------

function bod_organization_jsonld() {
	return bod_json(
		array(
			'@context'    => 'https://schema.org',
			'@type'       => 'Organization',
			'name'        => BOD_SITE_NAME,
			'description' => BOD_SITE_TAGLINE,
			'url'         => BOD_CANONICAL_ORIGIN,
			'logo'        => bod_image_url( 'logo.png' ),
			'sameAs'      => array(
				'https://bowlofdata.substack.com/',
				'https://www.instagram.com/bowl_of_data',
				BOD_PODCAST_URL,
				BOD_YOUTUBE_URL,
			),
		)
	);
}

function bod_website_jsonld() {
	return bod_json(
		array(
			'@context'    => 'https://schema.org',
			'@type'       => 'WebSite',
			'name'        => BOD_SITE_NAME,
			'description' => BOD_SITE_TAGLINE,
			'url'         => BOD_CANONICAL_ORIGIN,
		)
	);
}

function bod_publisher_node() {
	return array(
		'@type' => 'Organization',
		'name'  => BOD_SITE_NAME,
		'url'   => BOD_CANONICAL_ORIGIN,
		'logo'  => array(
			'@type' => 'ImageObject',
			'url'   => bod_image_url( 'logo.png' ),
		),
	);
}

/**
 * CollectionPage + ItemList for one issue.
 *
 * @param array $issue    bod_issue_data() output.
 * @param array $articles Story arrays.
 */
function bod_week_jsonld( $issue, $articles ) {
	$count     = count( $articles );
	$week_url  = BOD_CANONICAL_ORIGIN . '/' . $issue['href'];
	$publisher = bod_publisher_node();
	$week_date = bod_date_from_mtime( $issue['source_mtime'] );
	$og_image  = bod_image_url( 'bowl.png' );

	$items = array();
	foreach ( $articles as $i => $a ) {
		$node = array(
			'@type'     => 'NewsArticle',
			'headline'  => $a['title'],
			'url'       => $a['url'] ? $a['url'] : $week_url . '#' . $a['slug'],
			'image'     => $og_image,
			'publisher' => $publisher,
			'author'    => array(
				'@type' => 'Organization',
				'name'  => BOD_SITE_NAME,
				'url'   => BOD_CANONICAL_ORIGIN,
			),
		);
		if ( ! empty( $a['short_summary'] ) ) {
			$node['description'] = $a['short_summary'];
		}
		if ( ! empty( $a['published'] ) ) {
			$node['datePublished'] = $a['published'];
		} elseif ( $week_date ) {
			$node['datePublished'] = $week_date;
		}
		$items[] = array(
			'@type'    => 'ListItem',
			'position' => $i + 1,
			'item'     => $node,
		);
	}

	$page = array(
		'@context'    => 'https://schema.org',
		'@type'       => 'CollectionPage',
		'name'        => $issue['label'] . ' · ' . BOD_SITE_NAME,
		'description' => $count . ' article' . bod_plural( $count ) . ' curated this week covering AI, cybersecurity, blockchain and engineering.',
		'url'         => $week_url,
		'publisher'   => $publisher,
		'mainEntity'  => array(
			'@type'           => 'ItemList',
			'numberOfItems'   => $count,
			'itemListElement' => $items,
		),
	);
	if ( $week_date ) {
		$page['datePublished'] = $week_date;
		$page['dateModified']  = $week_date;
	}

	return bod_json( $page );
}

/**
 * CollectionPage + ItemList for a topic hub or tag page.
 *
 * @param string $name        Schema name.
 * @param string $description Schema description.
 * @param string $url         Canonical URL.
 * @param array  $items       Story arrays carrying week_href and date.
 */
function bod_collection_jsonld( $name, $description, $url, $items ) {
	$publisher = bod_publisher_node();
	$og_image  = bod_image_url( 'bowl.png' );

	$list = array();
	foreach ( $items as $i => $it ) {
		$node = array(
			'@type'     => 'NewsArticle',
			'headline'  => $it['title'],
			'url'       => BOD_CANONICAL_ORIGIN . '/' . $it['week_href'] . '#' . $it['slug'],
			'image'     => $og_image,
			'publisher' => $publisher,
			'author'    => array(
				'@type' => 'Organization',
				'name'  => BOD_SITE_NAME,
				'url'   => BOD_CANONICAL_ORIGIN,
			),
		);
		if ( ! empty( $it['short_summary'] ) ) {
			$node['description'] = $it['short_summary'];
		}
		if ( ! empty( $it['date'] ) ) {
			$node['datePublished'] = $it['date'];
		}
		$list[] = array(
			'@type'    => 'ListItem',
			'position' => $i + 1,
			'item'     => $node,
		);
	}

	return bod_json(
		array(
			'@context'    => 'https://schema.org',
			'@type'       => 'CollectionPage',
			'name'        => $name,
			'description' => $description,
			'url'         => $url,
			'publisher'   => $publisher,
			'mainEntity'  => array(
				'@type'           => 'ItemList',
				'numberOfItems'   => count( $items ),
				'itemListElement' => $list,
			),
		)
	);
}

/**
 * BreadcrumbList.
 *
 * @param array $crumbs List of array( name, url|null ).
 */
function bod_breadcrumb_jsonld( $crumbs ) {
	$elements = array();
	foreach ( $crumbs as $i => $crumb ) {
		list( $name, $url ) = $crumb;
		$el                 = array(
			'@type'    => 'ListItem',
			'position' => $i + 1,
			'name'     => $name,
		);
		if ( $url ) {
			$el['item'] = $url;
		}
		$elements[] = $el;
	}

	return bod_json(
		array(
			'@context'        => 'https://schema.org',
			'@type'           => 'BreadcrumbList',
			'itemListElement' => $elements,
		)
	);
}

/**
 * FAQPage, for the about and services pages.
 *
 * @param array $qa List of array( question, answer ).
 */
function bod_faq_jsonld( $qa ) {
	$entities = array();
	foreach ( $qa as $pair ) {
		$entities[] = array(
			'@type'          => 'Question',
			'name'           => $pair[0],
			'acceptedAnswer' => array(
				'@type' => 'Answer',
				'text'  => $pair[1],
			),
		);
	}
	return bod_json(
		array(
			'@context'   => 'https://schema.org',
			'@type'      => 'FAQPage',
			'mainEntity' => $entities,
		)
	);
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

/** Port of subscribeCta(). */
function bod_subscribe_cta( $ctx = 'inline' ) {
	$href = BOD_SUBSTACK_URL . '?utm_source=bowlofdata&amp;utm_medium=site&amp;utm_campaign=' . rawurlencode( $ctx );

	return '
<section class="subscribe-cta" aria-label="Subscribe to Bowl of Data">
  <div class="subscribe-cta-inner">
    <p class="subscribe-cta-kicker">Free weekly digest</p>
    <h2 class="subscribe-cta-title">Get next Saturday&rsquo;s issue in your inbox</h2>
    <p class="subscribe-cta-sub">
      The week&rsquo;s most relevant AI, security, blockchain, and engineering stories —
      curated, summarised, and reviewed by humans. No spam, unsubscribe anytime.
    </p>
    <a href="' . $href . '"
       class="cta-primary" target="_blank" rel="noopener">Subscribe — it&rsquo;s free</a>
  </div>
</section>';
}

/**
 * Port of articleCard(). Shared by the issue page's articles and papers.
 *
 * @param array  $a               Story array.
 * @param int    $index           1-based position.
 * @param string $number_label    "Article" or "Paper".
 * @param string $read_more_label "Read full article" or "Read paper".
 * @param array  $linkable_tags   slug => true map from bod_linkable_tag_slugs().
 */
function bod_article_card( $a, $index, $number_label, $read_more_label, $linkable_tags ) {
	$paras = ! empty( $a['long_resume_paragraphs'] ) ? $a['long_resume_paragraphs'] : array();
	$techs = ! empty( $a['technologies'] ) ? $a['technologies'] : array();

	$tags_html = '';
	if ( $techs ) {
		$pills = array();
		foreach ( $techs as $tech ) {
			$tslug   = bod_slugify( $tech );
			$pills[] = isset( $linkable_tags[ $tslug ] )
				? '<a class="tag tag--link" href="' . esc_url( bod_url( '/tag/' . $tslug . '.html' ) ) . '">' . bod_esc( $tech ) . '</a>'
				: '<span class="tag">' . bod_esc( $tech ) . '</span>';
		}
		$tags_html = '<div class="article-tags">
            ' . implode( "\n            ", $pills ) . '
          </div>';
	}

	$title_html = $a['url']
		? '<a href="' . esc_url( $a['url'] ) . '" target="_blank" rel="noopener">' . bod_esc( $a['title'] ) . '</a>'
		: bod_esc( $a['title'] );

	$beat_html = ! empty( $a['category_label'] )
		? '<a class="beat-badge beat-badge--' . bod_esc( $a['category'] ) . '" href="' . esc_url( bod_url( '/topic/' . $a['category'] . '.html' ) ) . '">' . bod_esc( $a['category_label'] ) . '</a>'
		: '';

	$source_html = ! empty( $a['source'] ) ? '<span class="article-source">' . bod_esc( $a['source'] ) . '</span>' : '';
	$topic_html  = ! empty( $a['main_topic'] ) ? '<p class="article-topic">' . bod_esc( $a['main_topic'] ) . '</p>' : '';

	$tldr_html = ! empty( $a['short_summary'] )
		? '<div class="tldr-box">
            <p class="tldr-label">TL;DR</p>
            <p class="tldr-text">' . bod_esc( $a['short_summary'] ) . '</p>
          </div>'
		: '';

	$resume_html = '';
	if ( $paras ) {
		$wrapped = array_map(
			static function ( $p ) {
				return '<p>' . bod_esc( $p ) . '</p>';
			},
			$paras
		);
		$resume_html = '<div class="long-resume">
            ' . implode( "\n            ", $wrapped ) . '
          </div>';
	}

	$read_more = $a['url']
		? '<a class="read-more" href="' . esc_url( $a['url'] ) . '" target="_blank" rel="noopener">' . bod_esc( $read_more_label ) . ' →</a>'
		: '';

	return '      <article class="article-card" id="' . bod_esc( $a['slug'] ) . '">

        <div class="article-card-top">
          <p class="article-number">' . bod_esc( $number_label ) . ' ' . (int) $index . '</p>
          <h2 class="article-title">
            ' . $title_html . '
          </h2>
          <div class="article-meta">
            ' . $beat_html . '
            ' . $source_html . '
          </div>
        </div>

        <div class="article-card-body">
          ' . $topic_html . '
          ' . $tldr_html . '
          ' . $resume_html . '
        </div>

        <div class="article-card-footer">
          ' . $tags_html . '
          ' . $read_more . '
        </div>

      </article>';
}

/** Port of releaseCard(). */
function bod_release_card( $item ) {
	$feats = ! empty( $item['key_features'] ) ? $item['key_features'] : array();

	$date_html = ( ! empty( $item['release_date'] ) && 'recent' !== $item['release_date'] )
		? '<span class="release-date-pill">' . bod_esc( $item['release_date'] ) . '</span>'
		: '';

	$name_html = ! empty( $item['url'] )
		? '<a href="' . esc_url( $item['url'] ) . '" target="_blank" rel="noopener">' . bod_esc( $item['model_name'] ) . '</a>'
		: bod_esc( $item['model_name'] );

	$summary_html = ! empty( $item['summary'] ) ? '<p class="release-summary">' . bod_esc( $item['summary'] ) . '</p>' : '';

	$feats_html = '';
	if ( $feats ) {
		$lis        = array_map(
			static function ( $f ) {
				return '<li>' . bod_esc( $f ) . '</li>';
			},
			$feats
		);
		$feats_html = '<ul class="release-features">
              ' . implode( "\n              ", $lis ) . '
            </ul>';
	}

	$footer_html = ! empty( $item['url'] )
		? '<div class="release-card-footer">
            <a href="' . esc_url( $item['url'] ) . '" class="release-read-link" target="_blank" rel="noopener">Read announcement →</a>
          </div>'
		: '';

	return '        <article class="release-card" id="' . bod_esc( $item['slug'] ) . '">

          <div class="release-card-top">
            <div class="release-meta-row">
              <span class="release-provider-tag">' . bod_esc( $item['provider'] ) . '</span>
              ' . $date_html . '
            </div>
            <h3 class="release-name">
              ' . $name_html . '
            </h3>
          </div>

          <div class="release-card-body">
            ' . $summary_html . '
            ' . $feats_html . '
          </div>

          ' . $footer_html . '

        </article>';
}

/**
 * Port of renderCollection() — the body shared by topic hubs and tag pages.
 *
 * @param array $c kicker, h1, intro, count, groups[], related_topics[], related_tags[].
 */
function bod_render_collection_body( $c ) {
	$issue_count = count( $c['groups'] );

	$chips = '';
	if ( ! empty( $c['related_topics'] ) ) {
		$links = array();
		foreach ( $c['related_topics'] as $t ) {
			$links[] = '<a href="' . esc_url( bod_url( '/topic/' . $t['slug'] . '.html' ) ) . '" class="chip chip--beat">' . bod_esc( $t['label'] ) . '</a>';
		}
		$chips .= '
    <div class="collection-chips">
      ' . implode( "\n      ", $links ) . '
    </div>';
	}
	if ( ! empty( $c['related_tags'] ) ) {
		$links = array();
		foreach ( $c['related_tags'] as $t ) {
			$links[] = '<a href="' . esc_url( bod_url( '/tag/' . $t['slug'] . '.html' ) ) . '" class="chip">' . bod_esc( $t['name'] ) . ' <span>' . (int) $t['count'] . '</span></a>';
		}
		$chips .= '
    <div class="collection-chips">
      ' . implode( "\n      ", $links ) . '
    </div>';
	}

	$groups_html = array();
	foreach ( $c['groups'] as $g ) {
		$entries = array();
		foreach ( $g['entries'] as $it ) {
			$sum = ! empty( $it['short_summary'] ) ? '<p class="collection-item-sum">' . bod_esc( $it['short_summary'] ) . '</p>' : '';
			$src = ! empty( $it['source'] ) ? '<span class="collection-item-src">' . bod_esc( $it['source'] ) . '</span>' : '';
			$ext = ! empty( $it['url'] ) ? '<a href="' . esc_url( $it['url'] ) . '" target="_blank" rel="noopener" class="collection-item-ext">Source ↗</a>' : '';

			$entries[] = '      <li class="collection-item">
        <a href="' . esc_url( bod_url( '/' . $it['week_href'] ) ) . '#' . bod_esc( $it['slug'] ) . '" class="collection-item-title">' . bod_esc( $it['title'] ) . '</a>
        ' . $sum . '
        <div class="collection-item-meta">
          <span class="chip chip--beat">' . bod_esc( $it['category_label'] ) . '</span>
          ' . $src . '
          ' . $ext . '
        </div>
      </li>';
		}

		$groups_html[] = '  <section class="collection-group">
    <div class="collection-group-head">
      <h2 class="collection-group-title">' . bod_esc( $g['label'] ) . '</h2>
      <a href="' . esc_url( bod_url( '/' . $g['week_href'] ) ) . '" class="collection-group-link">Read the issue →</a>
    </div>
    <ul class="collection-list">
' . implode( "\n", $entries ) . '
    </ul>
  </section>';
	}

	return '<div class="collection-header">
  <div class="collection-header-inner">
    <a href="' . esc_url( bod_url( '/topics.html' ) ) . '" class="back-link">← All topics</a>
    <p class="collection-kicker">' . bod_esc( $c['kicker'] ) . '</p>
    <h1 class="collection-title">' . bod_esc( $c['h1'] ) . '</h1>
    <p class="collection-intro">' . bod_esc( $c['intro'] ) . '</p>
    <p class="collection-meta">' . (int) $c['count'] . ' item' . bod_plural( $c['count'] ) . ' · ' . $issue_count . ' issue' . bod_plural( $issue_count ) . '</p>
' . $chips . '
  </div>
</div>

<div class="collection-body">
' . implode( "\n", $groups_html ) . '
</div>
' . bod_subscribe_cta( 'topic' );
}
