// Main JavaScript for Gaming Store
const bootstrap = window.bootstrap // Declare the bootstrap variable

document.addEventListener("DOMContentLoaded", () => {
  // Initialize tooltips
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl))

  // Check for notifications
  checkNotifications()

  // Auto-hide alerts after 5 seconds
  // setTimeout(() => {
  //   var alerts = document.querySelectorAll(".alert")
  //   alerts.forEach((alert) => {
  //     var bsAlert = new bootstrap.Alert(alert)
  //     bsAlert.close()
  //   })
  // }, 5000)
})

// Check for unread notifications
function checkNotifications() {
  // This would typically make an AJAX call to check for notifications
  // For now, we'll just show the badge if there are notifications on the page
  const notifications = document.querySelectorAll(".alert-info")
  const badge = document.getElementById("notificationBadge")

  if (notifications.length > 0 && badge) {
    badge.textContent = notifications.length
    badge.style.display = "inline"
  }
}

// Voice preview functionality
function playVoicePreview(audioUrl) {
  const audio = new Audio(audioUrl)
  audio.play().catch((error) => {
    console.log("Audio playback failed:", error)
    alert("Unable to play audio preview")
  })
}

// Game filtering
function filterGames(genre) {
  const gameCards = document.querySelectorAll(".game-card")

  gameCards.forEach((card) => {
    const cardGenre = card.dataset.genre

    if (genre === "" || cardGenre === genre) {
      card.style.display = "block"
    } else {
      card.style.display = "none"
    }
  })
}

// Search functionality
function searchGames(query) {
  const gameCards = document.querySelectorAll(".game-card")
  const searchQuery = query.toLowerCase()

  gameCards.forEach((card) => {
    const title = card.querySelector(".card-title").textContent.toLowerCase()
    const description = card.querySelector(".card-text").textContent.toLowerCase()

    if (title.includes(searchQuery) || description.includes(searchQuery)) {
      card.style.display = "block"
    } else {
      card.style.display = "none"
    }
  })
}

// Rating stars interaction
function setRating(rating) {
  const stars = document.querySelectorAll(".rating-star")

  stars.forEach((star, index) => {
    if (index < rating) {
      star.classList.add("active")
    } else {
      star.classList.remove("active")
    }
  })
}

// Cart functionality
function updateCartCount() {
  // This would typically make an AJAX call to get cart count
  const cartBadge = document.querySelector(".cart-badge")
  if (cartBadge) {
    // Update cart count
  }
}

// Setup image preview
function previewSetupImage(input) {
  if (input.files && input.files[0]) {
    const reader = new FileReader()

    reader.onload = (e) => {
      const preview = document.getElementById("imagePreview")
      if (preview) {
        preview.src = e.target.result
        preview.style.display = "block"
      }
    }

    reader.readAsDataURL(input.files[0])
  }
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault()

    const target = document.querySelector(this.getAttribute("href"))
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
      })
    }
  })
})

// Form validation
function validateForm(formId) {
  const form = document.getElementById(formId)
  const inputs = form.querySelectorAll("input[required], textarea[required], select[required]")
  let isValid = true

  inputs.forEach((input) => {
    if (!input.value.trim()) {
      input.classList.add("is-invalid")
      isValid = false
    } else {
      input.classList.remove("is-invalid")
    }
  })

  return isValid
}

// Loading spinner
function showLoading() {
  const spinner = document.createElement("div")
  spinner.className = "spinner-border text-primary"
  spinner.setAttribute("role", "status")
  spinner.innerHTML = '<span class="visually-hidden">Loading...</span>'

  document.body.appendChild(spinner)
}

function hideLoading() {
  const spinner = document.querySelector(".spinner-border")
  if (spinner) {
    spinner.remove()
  }
}

// Error handling
function showError(message) {
  const alert = document.createElement("div")
  alert.className = "alert alert-danger alert-dismissible fade show"
  alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `

  const container = document.querySelector(".container")
  container.insertBefore(alert, container.firstChild)
}

// Success message
function showSuccess(message) {
  const alert = document.createElement("div")
  alert.className = "alert alert-success alert-dismissible fade show"
  alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `

  const container = document.querySelector(".container")
  container.insertBefore(alert, container.firstChild)
}
