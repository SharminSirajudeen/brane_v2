// Smooth scroll to sections
document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');

            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => {
                btn.classList.remove('active');
                btn.classList.add('bg-white/10', 'text-gray-300');
                btn.classList.remove('bg-primary', 'text-white');
            });

            tabContents.forEach(content => {
                content.classList.add('hidden');
                content.classList.remove('active');
            });

            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            button.classList.remove('bg-white/10', 'text-gray-300');
            button.classList.add('bg-primary', 'text-white');

            const activeContent = document.querySelector(`.tab-content[data-tab="${tabName}"]`);
            if (activeContent) {
                activeContent.classList.remove('hidden');
                activeContent.classList.add('active');
            }
        });
    });

    // Demo modal functionality
    const demoBtn = document.getElementById('demo-btn');
    const demoModal = document.getElementById('demo-modal');
    const closeModal = document.getElementById('close-modal');

    if (demoBtn && demoModal) {
        demoBtn.addEventListener('click', () => {
            demoModal.classList.remove('hidden');
            demoModal.classList.add('flex');
            document.body.style.overflow = 'hidden';
        });
    }

    if (closeModal && demoModal) {
        closeModal.addEventListener('click', () => {
            demoModal.classList.add('hidden');
            demoModal.classList.remove('flex');
            document.body.style.overflow = 'auto';
        });

        // Close on backdrop click
        demoModal.addEventListener('click', (e) => {
            if (e.target === demoModal) {
                demoModal.classList.add('hidden');
                demoModal.classList.remove('flex');
                document.body.style.overflow = 'auto';
            }
        });
    }

    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe all sections
    const sections = document.querySelectorAll('section');
    sections.forEach(section => {
        observer.observe(section);
    });

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && demoModal && !demoModal.classList.contains('hidden')) {
            demoModal.classList.add('hidden');
            demoModal.classList.remove('flex');
            document.body.style.overflow = 'auto';
        }
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Add loading animation to external links
    document.querySelectorAll('a[href^="http"]').forEach(link => {
        link.addEventListener('click', function(e) {
            if (!this.hasAttribute('data-no-loading')) {
                this.style.opacity = '0.7';
                this.style.pointerEvents = 'none';

                setTimeout(() => {
                    this.style.opacity = '1';
                    this.style.pointerEvents = 'auto';
                }, 1000);
            }
        });
    });

    // Parallax effect for hero background
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.absolute.inset-0 > div');

        parallaxElements.forEach((el, index) => {
            const speed = (index + 1) * 0.1;
            el.style.transform = `translateY(${scrolled * speed}px)`;
        });
    });

    // Add fade-in animation to elements as they come into view
    const fadeElems = document.querySelectorAll('.group');

    const fadeObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    fadeElems.forEach(elem => {
        elem.style.opacity = '0';
        elem.style.transform = 'translateY(20px)';
        elem.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        fadeObserver.observe(elem);
    });

    // Dynamic year in footer
    const yearElements = document.querySelectorAll('[data-year]');
    const currentYear = new Date().getFullYear();
    yearElements.forEach(el => {
        el.textContent = currentYear;
    });

    // Track scroll depth for analytics (placeholder)
    let maxScroll = 0;
    window.addEventListener('scroll', () => {
        const scrollPercent = (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100;
        if (scrollPercent > maxScroll) {
            maxScroll = scrollPercent;
            // Analytics tracking would go here
            // console.log('Max scroll depth:', Math.round(maxScroll), '%');
        }
    });

    // Add active state to navigation on scroll
    const navLinks = document.querySelectorAll('a[href^="#"]');
    const sectionElements = Array.from(sections);

    window.addEventListener('scroll', () => {
        const scrollPosition = window.scrollY + 100;

        sectionElements.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute('id');

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === `#${sectionId}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    });

    // Preload critical assets
    const preloadImages = () => {
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        });
    };

    // Run preload after page load
    if (document.readyState === 'complete') {
        preloadImages();
    } else {
        window.addEventListener('load', preloadImages);
    }

    // Add touch-friendly hover effects for mobile
    if ('ontouchstart' in window) {
        document.querySelectorAll('.group').forEach(elem => {
            elem.addEventListener('touchstart', function() {
                this.classList.add('touched');
            });
            elem.addEventListener('touchend', function() {
                setTimeout(() => {
                    this.classList.remove('touched');
                }, 300);
            });
        });
    }

    // Performance monitoring (placeholder)
    if ('PerformanceObserver' in window) {
        const perfObserver = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                // Log performance metrics
                // console.log('Performance:', entry.name, entry.duration);
            }
        });

        perfObserver.observe({ entryTypes: ['measure', 'navigation'] });
    }
});
