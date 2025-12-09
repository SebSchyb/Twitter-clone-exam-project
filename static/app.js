const burger = document.querySelector(".burger");
const nav = document.querySelector("nav");

// ##############################
async function server(url, method, data_source_selector, function_after_fetch) {
    let conn = null;
    if (method.toUpperCase() == "POST") {
        const data_source = document.querySelector(data_source_selector);
        conn = await fetch(url, {
            method: method,
            body: new FormData(data_source),
        });
    }
    const data_from_server = await conn.text();
    if (!conn) {
        console.log("error connecting to the server");
    }
    window[function_after_fetch](data_from_server);
}

// ##############################
function get_search_results(
    url,
    method,
    data_source_selector,
    function_after_fetch
) {
    const txt_search_for = document.querySelector("#txt_search_for");
    if (txt_search_for.value == "") {
        console.log("empty search");
        document.querySelector("#search_results").innerHTML = "";
        document.querySelector("#search_results").classList.add("d-none");
        return false;
    }
    server(url, method, data_source_selector, function_after_fetch);
}
// ##############################
function parse_search_results(data_from_server) {
    // console.log(data_from_server)
    data_from_server = JSON.parse(data_from_server);
    let users = "";
    data_from_server.forEach((user) => {
        let user_avatar_path = user.user_avatar_path
            ? user.user_avatar_path
            : "unknown.jpg";
        let html = `
        <div class="d-flex a-items-center">
            <a href="/${user.user_username}" mix-get onclick="mixhtml(); return false">
                <img src="/static/images/${user_avatar_path}" class="w-8 h-8 rounded-full name pointer-e-none" alt="Profile Picture">
            </a>     
            <div class="w-full ml-2">
                <a href="/${user.user_username}" mix-get onclick="mixhtml(); return false">
                    <p class="name pointer-e-none">
                            ${user.user_first_name} ${user.user_last_name}
                        <span class="text-c-gray:+20 text-70">@${user.user_username}</span>
                    </p>   
                </a>             
            </div>
        </div>`;
        users += html;
    });
    console.log(users);
    document.querySelector("#search_results").innerHTML = users;
    document.querySelector("#search_results").classList.remove("d-none");
}

// ##############################
burger.addEventListener("click", () => {
    nav.classList.toggle("active");

    burger.classList.toggle("open");
});

//  Handle like/unlike
//  ##############################
document.addEventListener("click", async function (event) {
    const btn = event.target.closest(".like-btn");
    if (!btn) return;

    event.preventDefault();
    const postPk = btn.dataset.post;

    btn.disabled = true;

    const resp = await fetch("/toggle_like", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ post_pk: postPk }),
    });

    const data = await resp.json();

    const icon = btn.querySelector("i");
    const count = btn.querySelector(".like-count");

    count.textContent = data.like_count;

    if (data.liked) {
        icon.classList.remove("fa-regular");
        icon.classList.add("fa-solid");
    } else {
        icon.classList.remove("fa-solid");
        icon.classList.add("fa-regular");
    }

    btn.disabled = false;
});

//Handle follow/unfollow
// ##############################
document.addEventListener("click", async function (event) {
    const btn = event.target.closest(".follow-button");
    if (!btn) return;

    event.preventDefault();
    const userPk = btn.dataset.user;

    btn.disabled = true;

    const resp = await fetch("/toggle_follow", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ user_pk: userPk }),
    });

    const data = await resp.json();

    if (data.followed) {
        btn.textContent = "Unfollow";
        btn.classList.remove("bg-c-black");
        btn.classList.add("bg-c-blue");
    } else {
        btn.textContent = "Follow";
        btn.classList.add("bg-c-black");
        btn.classList.remove("bg-c-blue");
    }

    btn.disabled = false;
});
// Close details when clicking
//  ##############################
document.addEventListener("click", (e) => {
    document.querySelectorAll("details.menu[open]").forEach((openMenu) => {
        if (!openMenu.contains(e.target)) {
            openMenu.removeAttribute("open");
        }
    });
});

document.addEventListener("click", function (e) {
    // If an edit button is clicked
    if (e.target.classList.contains("edit-btn")) {
        const postId = e.target.dataset.post;

        // Show modal
        document
            .getElementById(`editModal-${postId}`)
            .classList.remove("hidden");
    }
});

function closeAllModals() {
    document.querySelectorAll(".modal").forEach((modal) => {
        modal.classList.add("hidden");
    });
}
// CLOSE when clicking the close button (ANY modal)
document.addEventListener("click", function (e) {
    if (e.target.classList.contains("close")) {
        closeAllModals();
    }
});

// CLOSE when clicking OUTSIDE any modal-content
document.addEventListener("click", function (e) {
    if (e.target.classList.contains("modal")) {
        closeAllModals();
    }
});

document.addEventListener("submit", (e) => {
    e.preventDefault();
    closeAllModals();
    e.target.reset();
});

document.addEventListener("click", (event) => {
    const closeBtn = event.target.closest(".close-edit");
    if (!closeBtn) return;

    const details = closeBtn.closest("details.profile-edit");
    if (details) {
        details.open = false;
    }
});

document.addEventListener("submit", (event) => {
    const form = event.target.closest(".profile-edit-form");
    if (!form) return;

    const details = form.closest("details.profile-edit");
    if (details) {
        details.open = false;
    }
});
