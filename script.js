document.addEventListener('DOMContentLoaded', function() {
    const cartCountSpan = document.getElementById('cart-count');
    const addToCartForms = document.querySelectorAll('.add-to-cart-form');

    addToCartForms.forEach(form => {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            const formData = new FormData(this);
            const productId = formData.get('product_id'); // Get product_id from form data
            console.log(`JavaScript - Sending product_id: ${productId}, Type: ${typeof productId}`); // Debugging

            fetch('/add_to_cart', {
                method: 'POST',
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    alert(data.message);
                    cartCountSpan.textContent = data.cart_count;
                }
            })
            .catch(error => {
                console.error('Error adding to cart:', error);
            });
        });
    });
});