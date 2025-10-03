```markdown
# Organization Branding & Personalization System

## Overview

The Sports League Management System now features comprehensive organization branding and personalization capabilities, allowing each organization to create a unique, branded experience for their users.

## Features Implemented

### 1. **Org-Branded Landing Pages**
Custom landing pages that automatically adapt based on the organization accessing the system.

**Template:** `slms/templates/org_landing.html`

**Features:**
- Dynamic hero section with customizable content
- Organization logo and branding colors
- Animated background effects
- Quick stats showcase
- Modular content sections
- Fully responsive design

### 2. **Hero Section Customization**
Fully customizable hero sections for maximum impact.

**Configurable Elements:**
- **Title & Subtitle** - Main messaging
- **Gradient Colors** - Start and end colors for background
- **Background Image** - Optional hero background
- **Hero Image** - Optional right-side image/illustration
- **CTA Buttons** - Up to 2 call-to-action buttons with custom text, URLs, and icons
- **Feature Highlights** - Up to 3 key features displayed below CTAs

**Default Configuration:**
```python
{
    'title': 'Organization Name',
    'subtitle': 'Experience world-class sports management',
    'gradient_start': '#667eea',
    'gradient_end': '#764ba2',
    'primary_cta_text': 'View Standings',
    'primary_cta_url': '/standings',
    'primary_cta_icon': 'trophy',
    'secondary_cta_text': 'Stat Leaders',
    'secondary_cta_url': '/leaderboards',
    'secondary_cta_icon': 'chart-line',
    'features': ['Real-time Updates', 'Complete Statistics', 'Fan Engagement']
}
```

### 3. **Domain-Based Theme Loading**
Automatic organization detection and theme application based on domain.

**Service:** `slms/services/domain_loader.py`

**Detection Methods:**
1. **Custom Domain** - `sports.myorg.com` → Loads "MyOrg" organization
2. **Subdomain** - `myorg.sportslms.com` → Loads "MyOrg" organization
3. **URL Slug** - `/org/myorg` → Loads "MyOrg" organization

**How It Works:**
```python
# Automatically runs on every request
@app.before_request
def load_org_branding():
    # Detects organization from domain/URL
    org, source = load_org_by_domain()

    # Injects into Flask g object
    g.org = org
    g.theme = get_org_theme(org)
    g.hero = get_org_hero_config(org)
    g.modules = get_org_modules(org)
```

### 4. **Page Module System**
Modular content sections for building custom landing pages.

**Available Module Types:**

#### Features Grid
```python
{
    'type': 'features',
    'title': 'Everything You Need',
    'subtitle': 'Comprehensive tools...',
    'features': [
        {
            'icon': 'trophy',
            'color': '#667eea',
            'title': 'Live Standings',
            'description': 'Real-time updates...'
        }
    ]
}
```

#### CTA Banner
```python
{
    'type': 'cta_banner',
    'title': 'Ready to Join?',
    'description': 'Get started today',
    'gradient_start': '#667eea',
    'gradient_end': '#764ba2',
    'cta_text': 'Sign Up Now',
    'cta_url': '/signup'
}
```

#### Testimonials
```python
{
    'type': 'testimonials',
    'title': 'What People Say',
    'testimonials': [
        {
            'quote': 'Amazing platform!',
            'name': 'John Doe',
            'role': 'League Manager',
            'avatar': 'url/to/avatar.jpg'
        }
    ]
}
```

### 5. **Branding Management Interface**
Admin interface for configuring organization branding.

**Route:** `/admin/manage_branding`
**Template:** `slms/templates/manage_branding.html`

**Management Tabs:**

#### Hero Section Tab
- Title and subtitle configuration
- Gradient color pickers
- Background and hero image URLs
- CTA button configuration (text, URL, icons)
- Feature highlights editor
- Live preview

#### Page Modules Tab
- Add/remove/reorder modules
- Configure module content
- Drag-to-reorder functionality
- Module type selection

#### Brand Colors Tab
- Primary color
- Secondary color
- Accent color
- Background color
- Live color picker

#### Brand Assets Tab
- Organization logo URL
- Favicon URL
- Banner image URL

#### Custom Domain Tab
- Current subdomain display
- Custom domain configuration
- DNS setup instructions
- Domain verification

### 6. **Custom Domain Support**
Organizations can use their own domains.

**Setup Process:**
1. Configure custom domain in admin panel
2. Add CNAME DNS record pointing to platform
3. Verify domain ownership
4. Automatic SSL certificate provisioning (future)

**Database Schema:**
```sql
-- Organization table already includes:
custom_domain VARCHAR(255) UNIQUE
```

**Example Configuration:**
```
Organization: "Elite Sports League"
Subdomain: elitesports.sportslms.com
Custom Domain: sports.eliteleague.com
```

## Database Schema

### Organization Model Fields

```python
class Organization(TimestampedBase):
    # Basic Info
    name: str
    slug: str  # Used for subdomain
    description: str | None

    # Branding
    primary_color: str | None
    secondary_color: str | None
    logo_url: str | None
    favicon_url: str | None
    banner_image_url: str | None
    custom_css: str | None

    # Custom Domain
    custom_domain: str | None  # Unique, indexed
```

### Future Enhancements (Recommended)

Create a `BrandingSettings` table for advanced configurations:

```sql
CREATE TABLE branding_settings (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organization(id),
    hero_config JSONB,
    modules_config JSONB,
    footer_config JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## API Endpoints

### Save Branding Configuration
```
POST /admin/api/branding/save
Content-Type: application/json

{
    "hero": {
        "title": "Welcome to Our League",
        "subtitle": "...",
        "gradient_start": "#667eea",
        "gradient_end": "#764ba2",
        ...
    },
    "branding": {
        "primary": "#667eea",
        "secondary": "#6c757d",
        "accent": "#f97316",
        "logo": "https://...",
        ...
    },
    "custom_domain": "sports.myorg.com"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Branding saved successfully"
}
```

## Usage Examples

### Example 1: Loading Org by Domain

```python
from slms.services.domain_loader import load_org_by_domain

# In a Flask route or before_request handler
org, source = load_org_by_domain()

if source == 'custom_domain':
    print(f"Loaded {org.name} via custom domain")
elif source == 'subdomain':
    print(f"Loaded {org.name} via subdomain")
```

### Example 2: Accessing Branding in Templates

```jinja2
<!-- Access organization info -->
{{ g.org.name }}
{{ g.org.logo_url }}

<!-- Access theme colors -->
{{ g.theme.palette.primary }}

<!-- Access hero config -->
{{ g.hero.title }}
{{ g.hero.subtitle }}

<!-- Loop through modules -->
{% for module in g.modules %}
    {% if module.type == 'features' %}
        <!-- Render features -->
    {% endif %}
{% endfor %}
```

### Example 3: Customizing Landing Page

```python
# In admin interface
@admin_bp.route('/manage_branding')
def manage_branding():
    hero = get_org_hero_config(g.org)
    modules = get_org_modules(g.org)

    return render_template('manage_branding.html',
                         hero=hero,
                         modules=modules)
```

## Integration Steps

### Step 1: Register Domain Loader

In your app factory (`slms/__init__.py`):

```python
from slms.services.domain_loader import register_domain_loader

def create_app():
    app = Flask(__name__)

    # Register domain loader
    register_domain_loader(app)

    return app
```

### Step 2: Add Branding to Navigation

Add link to admin navigation:

```python
{
    'label': 'Branding',
    'url': '/admin/manage_branding',
    'icon': 'palette'
}
```

### Step 3: Configure DNS (For Custom Domains)

1. Go to your DNS provider
2. Add CNAME record:
   ```
   Type: CNAME
   Name: sports (or subdomain)
   Value: yourdomain.sportslms.com
   TTL: 3600
   ```
3. Wait for DNS propagation (5-60 minutes)
4. Verify in admin panel

## Design Patterns

### Animated Hero Backgrounds

The landing page includes animated particle effects:

```css
.particle {
    position: absolute;
    width: 300px;
    height: 300px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 50%;
    animation: float 6s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-20px); }
}
```

### Fade-In Animations

Elements animate in on page load:

```css
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-fade-in-up {
    animation: fadeInUp 0.8s ease-out forwards;
}
```

### Responsive Stats Cards

Quick stats with hover effects:

```css
.stat-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}
```

## Best Practices

### 1. Hero Section
- Keep title under 50 characters
- Use high-contrast gradient colors
- Ensure text is readable over background
- Use compelling, action-oriented CTAs

### 2. Brand Colors
- Choose colors that represent your organization
- Ensure accessibility (WCAG AA compliance)
- Test on light and dark backgrounds
- Use consistent colors across all pages

### 3. Images
- **Logo:** PNG with transparent background, 500x500px minimum
- **Favicon:** ICO or PNG, 32x32px or 64x64px
- **Hero Image:** 800x600px minimum, high quality
- **Banner:** 1920x400px recommended

### 4. Custom Domains
- Use subdomain (sports.yourorg.com) not root domain
- Verify DNS configuration before going live
- Keep subdomain as fallback
- Test thoroughly before announcing

## Troubleshooting

### Issue: Organization Not Loading

**Check:**
1. DNS records are correct
2. `custom_domain` field is set in database
3. Domain matches exactly (case-insensitive)
4. Organization `is_active = True`

**Debug:**
```python
from slms.services.domain_loader import load_org_by_domain
org, source = load_org_by_domain()
print(f"Org: {org}, Source: {source}")
```

### Issue: Branding Not Applying

**Check:**
1. Branding fields are populated in database
2. Template is rendering `g.org` correctly
3. CSS is not being overridden
4. Cache is cleared

**Debug:**
```jinja2
<!-- In template -->
<pre>{{ g.org | tojson }}</pre>
<pre>{{ g.theme | tojson }}</pre>
```

### Issue: Custom Domain Not Working

**Check:**
1. DNS propagation complete (use `dig` or `nslookup`)
2. CNAME record points to correct host
3. No firewall blocking
4. SSL certificate valid

**Test DNS:**
```bash
dig sports.yourorg.com
nslookup sports.yourorg.com
```

## Security Considerations

### 1. Domain Verification
- Verify domain ownership before activation
- Check for typosquatting attempts
- Validate domain format

### 2. Custom CSS
- Sanitize custom CSS input
- Use CSP headers
- Prevent XSS attacks

### 3. Image URLs
- Validate image URLs
- Use HTTPS only
- Check file types
- Implement rate limiting

## Performance Optimization

### 1. Caching
```python
from flask_caching import Cache

cache = Cache(config={'CACHE_TYPE': 'simple'})

@cache.memoize(timeout=300)
def get_org_by_domain(host):
    return Organization.query.filter_by(custom_domain=host).first()
```

### 2. CDN Integration
- Serve static assets from CDN
- Cache images and logos
- Use lazy loading for hero images

### 3. Database Indexing
```sql
CREATE INDEX idx_org_custom_domain ON organization(custom_domain);
CREATE INDEX idx_org_slug ON organization(slug);
```

## Future Enhancements

### Planned Features
1. **Visual Module Builder** - Drag-and-drop interface
2. **Template Library** - Pre-built landing page templates
3. **A/B Testing** - Test different hero configurations
4. **Analytics Integration** - Track landing page performance
5. **Multi-language Support** - Translate landing pages
6. **Email Templates** - Branded email notifications
7. **Mobile App Theming** - Extend branding to mobile apps
8. **White-Label Reports** - Branded PDF exports

### Advanced Branding
- Custom fonts
- Advanced CSS editor
- Animation controls
- Video backgrounds
- Interactive elements

## Support

For questions or issues:
1. Check this documentation
2. Review template examples
3. Test with sample data
4. Contact development team

---

**Version:** 1.0
**Last Updated:** October 2025
**Author:** Sports League Management System Team
```
