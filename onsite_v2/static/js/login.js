let vm = new Vue({
    el: '#app',
    // 修改Vue变量的读取语法
    delimiters: ['[[', ']]'],
    data: {
        username: '',
        password: '',

        error_username: false,
        error_password: false,
        remembered: false,

        error_msg: '',
        error_show: false,
    },
    methods: {
        // 检查账号
        check_username(){
        	let re = /^[a-zA-Z0-9_-]{5,20}$/;
			if (re.test(this.username)) {
                this.error_username = false;
            } else {
                this.error_username = true;
            }
        },
		// 检查密码
        check_password(){
        	let re = /^[0-9A-Za-z]{5,20}$/;
			if (re.test(this.password)) {
                this.error_password = false;
            } else {
                this.error_password = true;
            }
        },
        // 表单提交
        on_submit(){
            this.check_username();
            this.check_password();

            if (this.error_username == true || this.error_password == true) {
                // 不满足登录条件：禁用表单
				window.event.returnValue = false
                alert('请检查账户名密码是否正确填写')
                return
            }
            axios.post('/user/auth/', {
                'username': this.username,
                'password': this.password,
                'remember': this.remember
            })
                .then(function (response){
                    sessionStorage.clear();
                    localStorage.clear();
                    localStorage.token = response.data.token;
                    localStorage.username = response.data.username;
                    localStorage.userid = response.data.id;
                    localStorage.level = response.data.level;
                    window.location.href = '/home/';
                })
                .catch(function (error){
                    alert('密码错误')
                })
        },
    }
});