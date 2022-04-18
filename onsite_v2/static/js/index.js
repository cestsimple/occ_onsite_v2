let vm = new Vue({
    el: '#app',
    // 修改Vue变量的读取语法
    delimiters: ['[[', ']]'],
    data: {
        nav_bar: '隐藏',
        user: {
            'id': 0,
            'name': '未登录',
            'level': 0,
        }
    },
    methods: {
        //退出登录
        fnQuit(){
              sessionStorage.clear();
              localStorage.clear();
              window.location.href = '/user/login/';
        },
        toUserCreatePage(){
            let url = '/user/register/';
            let header = {
                'authorization': 'Bearer ' + localStorage.token
            };
            axios.get(url, {
                headers: header
              })
                .then(function (response){
                    return
                })
                .catch(function (error){
                    alert('跳转失败，权限不足！');
                })
        },
        // 表单提交
        hide_nav(){
            if (this.nav_bar=='隐藏'){
                this.nav_bar = '显示';
            } else {
                this.nav_bar = '隐藏';
            }
        },
        fnUserInfo(){
            this.user.name = localStorage.username;
            this.user.id = localStorage.userid;
            this.user.level = localStorage.level;
        }
    },
    created: function (){
        let username = localStorage.username;
        if(username==undefined){
            window.location.href = '/user/login/';
            return;
        }
    },
    mounted: function (){
        this.fnUserInfo();
    }
});